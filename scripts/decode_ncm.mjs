#!/usr/bin/env node

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const [inputPath, outputPath] = process.argv.slice(2);
if (!inputPath || !outputPath) {
  throw new Error("Usage: node scripts/decode_ncm.mjs <input.ncm> <output-audio>");
}

const source = fs.readFileSync(inputPath);
if (source.subarray(0, 8).toString("ascii") !== "CTENFDAM") {
  throw new Error("Input is not an NCM container");
}

let offset = 10;
const encryptedKeyLength = source.readUInt32LE(offset);
offset += 4;
const encryptedKey = Buffer.from(source.subarray(offset, offset + encryptedKeyLength));
offset += encryptedKeyLength;
for (let index = 0; index < encryptedKey.length; index += 1) encryptedKey[index] ^= 0x64;

const decipher = crypto.createDecipheriv(
  "aes-128-ecb",
  Buffer.from("687a4852416d736f356b496e62617857", "hex"),
  null,
);
const keyPlaintext = Buffer.concat([decipher.update(encryptedKey), decipher.final()]);
const streamKey = keyPlaintext.subarray(17);
if (!streamKey.length) throw new Error("NCM stream key is empty");

const keyBox = Uint8Array.from({length: 256}, (_, index) => index);
let keyCursor = 0;
let swapIndex = 0;
for (let index = 0; index < 256; index += 1) {
  swapIndex = (keyBox[index] + swapIndex + streamKey[keyCursor]) & 0xff;
  [keyBox[index], keyBox[swapIndex]] = [keyBox[swapIndex], keyBox[index]];
  keyCursor = (keyCursor + 1) % streamKey.length;
}

const metadataLength = source.readUInt32LE(offset);
offset += 4 + metadataLength;
offset += 4; // CRC32
offset += 5; // container gap
const imageLength = source.readUInt32LE(offset);
const advertisedAudioOffset = offset + 4 + imageLength;

const streamMask = (index) => {
  const boxIndex = (index + 1) & 0xff;
  const maskIndex = (keyBox[boxIndex] + keyBox[(keyBox[boxIndex] + boxIndex) & 0xff]) & 0xff;
  return keyBox[maskIndex];
};

const encryptedMagic = (text) => Buffer.from(text, "ascii").map((byte, index) => byte ^ streamMask(index));
const magicCandidates = ["ID3", "fLaC", "OggS"];
let audioOffset = -1;
for (const magic of magicCandidates) {
  const found = source.indexOf(encryptedMagic(magic), offset);
  if (found >= 0 && (audioOffset < 0 || found < audioOffset)) audioOffset = found;
}
if (audioOffset < 0) audioOffset = advertisedAudioOffset;

const audio = Buffer.from(source.subarray(audioOffset));
for (let index = 0; index < audio.length; index += 1) {
  audio[index] ^= streamMask(index);
}

fs.mkdirSync(path.dirname(path.resolve(outputPath)), {recursive: true});
fs.writeFileSync(outputPath, audio);
console.log(JSON.stringify({inputPath, outputPath: path.resolve(outputPath), audioOffset, bytes: audio.length}));
