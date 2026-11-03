// 상세 이미지 글자 읽기 (macOS Vision, 한국어+영어). 레퍼런스 카피 분석용.
// 컴파일: swiftc -O pdp/scripts/ocr.swift -o <scratchpad>/ocr
// 사용: ocr <이미지> [<이미지> ...]
// 출력: 한 줄에 하나씩 JSON {"file","y","h","w","text"} (y·h·w는 원본 픽셀, 위에서부터). h가 큰 줄이 헤드라인이다.
import Foundation
import Vision
import AppKit

for path in CommandLine.arguments.dropFirst() {
    guard let img = NSImage(contentsOfFile: path),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        FileHandle.standardError.write("읽기 실패: \(path)\n".data(using: .utf8)!)
        continue
    }
    let W = Double(cg.width), H = Double(cg.height)
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.recognitionLanguages = ["ko-KR", "en-US"]
    req.usesLanguageCorrection = true
    do { try VNImageRequestHandler(cgImage: cg, options: [:]).perform([req]) } catch {
        FileHandle.standardError.write("OCR 실패: \(path) \(error)\n".data(using: .utf8)!)
        continue
    }
    let obs = (req.results ?? []).sorted { $0.boundingBox.maxY > $1.boundingBox.maxY }
    for o in obs {
        guard let t = o.topCandidates(1).first?.string else { continue }
        let b = o.boundingBox
        let row: [String: Any] = [
            "file": (path as NSString).lastPathComponent,
            "y": Int((1 - b.maxY) * H), "h": Int(b.height * H), "w": Int(b.width * W), "text": t,
        ]
        if let d = try? JSONSerialization.data(withJSONObject: row), let s = String(data: d, encoding: .utf8) { print(s) }
    }
}
