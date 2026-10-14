// scripts/vision_ocr.swift —— 逐字 OCR（macOS Vision，离线、确定性）
//
// 用途：给「封面/帧」做**逐字校验**，把"模型崩字 / 数字写错 / 编造数据"这类事故在发布前抓住。
// 背景（2026-09-14）：封面改为 GPT 出图后，中文正确性与数字正确性不再由我们的模板保证，
// 必须有一道客观门禁 —— 本工具就是那道门的眼睛。
//
// 编译：swiftc -O scripts/vision_ocr.swift -o scripts/bin/vision_ocr
// 用法：scripts/bin/vision_ocr a.png b.png …   → 打印 JSON：[{file, lines:[{t,c,x,y,h}]}]
import Foundation
import Vision
import AppKit

let args = CommandLine.arguments.dropFirst()
var out: [[String: Any]] = []
for path in args {
    guard let img = NSImage(contentsOfFile: path),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { continue }
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.recognitionLanguages = ["zh-Hans", "en-US"]
    req.usesLanguageCorrection = false
    let handler = VNImageRequestHandler(cgImage: cg, options: [:])
    try? handler.perform([req])
    var lines: [[String: Any]] = []
    for obs in (req.results ?? []) {
        guard let top = obs.topCandidates(1).first else { continue }
        let bb = obs.boundingBox
        lines.append(["t": top.string, "c": Double(top.confidence),
                      "y": Double(1 - bb.origin.y - bb.height), "x": Double(bb.origin.x),
                      "h": Double(bb.height), "w": Double(bb.width)])
    }
    lines.sort { ($0["y"] as! Double) < ($1["y"] as! Double) }
    out.append(["file": (path as NSString).lastPathComponent, "lines": lines])
}
let data = try! JSONSerialization.data(withJSONObject: out, options: [.prettyPrinted, .withoutEscapingSlashes])
FileHandle.standardOutput.write(data)
