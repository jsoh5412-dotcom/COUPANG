// 공급처 실제 제품 사진에서 배경을 지워 투명 PNG(누끼)로 저장한다.
// macOS 내장 Vision(전경 인스턴스 마스크)만 쓴다 — 외부 모델 다운로드·유료 API 없음.
// 제품의 형태·색은 건드리지 않는다. 마스크로 배경만 투명하게 하고, 피사체 범위로 잘라 낸다.
// 사용법: swift pdp/scripts/nukki.swift <입력 이미지> <출력.png> [--all | --largest] [--crop x,y,w,h]
//   --largest (기본): 가장 큰 피사체 하나만 남긴다
//   --all: 감지된 피사체를 모두 남긴다 (세트 구성품 등)
//   --crop: 입력에서 이 영역(px, 좌상단 기준)만 잘라 처리한다 (긴 상세 이미지 속 제품컷)
import AppKit
import CoreImage
import Vision

let args = CommandLine.arguments
guard args.count >= 3 else {
  FileHandle.standardError.write("usage: swift nukki.swift <in> <out.png> [--all|--largest] [--crop x,y,w,h]\n".data(using: .utf8)!)
  exit(1)
}
let keepAll = args.contains("--all")
var input = CIImage(contentsOf: URL(fileURLWithPath: args[1]))!
if let i = args.firstIndex(of: "--crop"), i + 1 < args.count {
  let v = args[i + 1].split(separator: ",").compactMap { Double($0) }
  // CIImage 좌표는 좌하단 기준이라 y를 뒤집는다
  let h = input.extent.height
  let r = CGRect(x: v[0], y: h - v[1] - v[3], width: v[2], height: v[3])
  input = input.cropped(to: r).transformed(by: CGAffineTransform(translationX: -r.minX, y: -r.minY))
}

let handler = VNImageRequestHandler(ciImage: input)
let req = VNGenerateForegroundInstanceMaskRequest()
try handler.perform([req])
guard let obs = req.results?.first, !obs.allInstances.isEmpty else {
  FileHandle.standardError.write("피사체를 찾지 못했습니다\n".data(using: .utf8)!)
  exit(2)
}

var instances = obs.allInstances
if !keepAll {
  // 인스턴스별 마스크 면적을 재서 가장 큰 것 하나만
  var best = instances.first!, bestArea = -1
  for inst in instances {
    let m = try obs.generateScaledMaskForImage(forInstances: [inst], from: handler)
    CVPixelBufferLockBaseAddress(m, .readOnly)
    let w = CVPixelBufferGetWidth(m), h = CVPixelBufferGetHeight(m), row = CVPixelBufferGetBytesPerRow(m)
    let base = CVPixelBufferGetBaseAddress(m)!.assumingMemoryBound(to: Float32.self)
    var area = 0
    for y in Swift.stride(from: 0, to: h, by: 4) {
      for x in Swift.stride(from: 0, to: w, by: 4) where base[y * row / 4 + x] > 0.5 { area += 1 }
    }
    CVPixelBufferUnlockBaseAddress(m, .readOnly)
    if area > bestArea { bestArea = area; best = inst }
  }
  instances = IndexSet(integer: best)
}

let masked = try obs.generateMaskedImage(ofInstances: instances, from: handler, croppedToInstancesExtent: true)
let out = CIImage(cvPixelBuffer: masked)
let ctx = CIContext()
let cs = CGColorSpace(name: CGColorSpace.sRGB)!
try ctx.writePNGRepresentation(of: out, to: URL(fileURLWithPath: args[2]), format: .RGBA8, colorSpace: cs)
print("ok \(args[2]) \(Int(out.extent.width))x\(Int(out.extent.height)) instances=\(instances.count)/\(obs.allInstances.count)")
