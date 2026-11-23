/**
 * 金标准对拍：JS 引擎必须与 Python 原实现逐位、逐字一致。
 *
 * 向量由 tools/export_golden.py 生成。改过 core/ 之后重跑该脚本，
 * 本测试变红即说明两套实现已经分叉。
 *
 * 运行：node --test web/tests/
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  RV32I_INSTRUCTIONS,
  PSEUDO_INSTRUCTIONS,
  REG_ALIASES,
  encode,
  decode,
  expandPseudo,
  getFormat,
} from '../src/core/isa.js';
import {
  assembleProgram,
  bytesToHexStr,
  disassembleBytes,
  pcrelParts,
} from '../src/core/assembler.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const golden = JSON.parse(fs.readFileSync(path.join(here, 'golden.json'), 'utf8'));

test('指令表与 Python 版完全一致', () => {
  const pyNames = Object.keys(golden.instructionTable);
  assert.deepEqual(Object.keys(RV32I_INSTRUCTIONS), pyNames);
  for (const name of pyNames) {
    assert.deepEqual(
      { ...RV32I_INSTRUCTIONS[name] },
      { ...golden.instructionTable[name] },
      `指令 ${name} 的属性不一致`,
    );
  }
});

test('伪指令集合与寄存器别名一致', () => {
  assert.deepEqual(Object.keys(PSEUDO_INSTRUCTIONS).sort(), golden.pseudoNames);
  assert.deepEqual({ ...REG_ALIASES }, golden.registers);
});

test(`编码向量 ${golden.encode.length} 条全部命中`, () => {
  for (const vec of golden.encode) {
    const word = encode(vec.mnemonic, vec.operands);
    assert.equal(word, vec.word, `${vec.asm} 编码结果不一致`);
    assert.equal(word.toString(16).padStart(8, '0'), vec.hex, `${vec.asm} 十六进制不一致`);

    const [name, operands] = decode(word);
    assert.equal(name, vec.decodeName, `${vec.asm} 反汇编指令名不一致`);
    assert.deepEqual(operands, vec.decodeOperands, `${vec.asm} 反汇编操作数不一致`);
  }
});

test(`错误向量 ${golden.errors.length} 条文案逐字一致`, () => {
  for (const vec of golden.errors) {
    assert.throws(
      () => encode(vec.mnemonic, vec.operands),
      (err) => {
        assert.equal(err.message, vec.error, `${vec.asm} 错误文案不一致`);
        return true;
      },
      `${vec.asm} 本应报错却没有报错`,
    );
  }
});

test(`伪指令向量 ${golden.pseudo.length} 条展开一致`, () => {
  for (const vec of golden.pseudo) {
    if (vec.error) {
      assert.throws(
        () => expandPseudo(vec.mnemonic, vec.operands),
        (err) => err.message === vec.error,
        `${vec.asm} 错误文案不一致`,
      );
      continue;
    }
    const expanded = expandPseudo(vec.mnemonic, vec.operands);
    assert.deepEqual(
      expanded.map(([m, o]) => [m, [...o]]),
      vec.expand,
      `${vec.asm} 展开序列不一致`,
    );
    expanded.forEach(([mnem, ops], i) => {
      const expected = vec.chunks[i];
      if (expected.error) {
        assert.throws(() => encode(mnem, ops), (err) => err.message === expected.error);
      } else {
        assert.equal(encode(mnem, ops), expected.word, `${vec.asm} 第 ${i + 1} 块编码不一致`);
      }
    });
  }
});

test(`程序样本 ${golden.programs.length} 个逐行一致`, () => {
  for (const sample of golden.programs) {
    const results = assembleProgram(sample.lines, sample.addrLines ?? null);
    assert.equal(results.length, sample.result.length, `${sample.name} 行数不一致`);

    sample.result.forEach((expected, i) => {
      const actual = results[i];
      const label = `${sample.name} 第 ${i + 1} 行`;
      assert.deepEqual(actual.labels, expected.labels, `${label} 标签不一致`);
      assert.equal(actual.address, expected.address, `${label} 地址不一致`);
      assert.equal(actual.size, expected.size, `${label} 字节数不一致`);
      assert.equal(actual.error, expected.error, `${label} 行级错误不一致`);
      assert.equal(actual.chunks.length, expected.chunks.length, `${label} 块数不一致`);

      expected.chunks.forEach((chunk, j) => {
        const got = actual.chunks[j];
        const where = `${label} 第 ${j + 1} 块`;
        assert.equal(got.mnemonic, chunk.mnemonic, `${where} 助记符不一致`);
        assert.equal(got.text, chunk.text, `${where} 文本不一致`);
        assert.equal(got.error, chunk.error, `${where} 块级错误不一致`);
        const le = got.data ? bytesToHexStr(got.data) : null;
        assert.equal(le, chunk.le, `${where} 机器码不一致`);
      });
    });
  }
});

test('已知机器码的反汇编结果', () => {
  const cases = [
    [0x06410093, 'addi x1, x2, 100'],
    [0xfe512c23, 'sw x5, -8(x2)'],
    [0x00000013, 'addi x0, x0, 0'],
    [0x00008067, 'jalr x0, x1, 0'],
    [0x00000073, 'ecall'],
    [0x00100073, 'ebreak'],
  ];
  for (const [word, expected] of cases) {
    const bytes = new Uint8Array([
      word & 0xff, (word >>> 8) & 0xff, (word >>> 16) & 0xff, (word >>> 24) & 0xff,
    ]);
    assert.equal(disassembleBytes(bytes), expected, `0x${word.toString(16)} 反汇编不一致`);
  }
});

test('getFormat 与 Python 版的类型友好名一致', () => {
  assert.equal(getFormat('add'), 'R-type');
  assert.equal(getFormat('lw'), 'I-type (Load)');
  // Python 版先查伪指令集合，"jalr" 同时存在于两个表中，因此返回 Pseudo
  assert.equal(getFormat('jalr'), 'Pseudo');
  assert.equal(getFormat('ecall'), 'System');
  assert.equal(getFormat('csrrw'), 'CSR');
  assert.equal(getFormat('fence'), 'Fence');
  assert.equal(getFormat('li'), 'Pseudo');
  assert.equal(getFormat('nope'), 'Unknown');
});

test('PC 相对拆分的进位修正', () => {
  assert.deepEqual(pcrelParts(0), [0, 0]);
  assert.deepEqual(pcrelParts(36), [0, 36]);
  assert.deepEqual(pcrelParts(0x800), [1, -2048]);
  assert.deepEqual(pcrelParts(0x1000), [1, 0]);
  assert.deepEqual(pcrelParts(-4), [0, -4]);
});
