// Original geometric app icon; no game artwork or official logos.
import AppKit
let directory = URL(fileURLWithPath: CommandLine.arguments[1])
try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
for size in [16, 32, 128, 256, 512] {
    for scale in [1, 2] {
        let pixels = size * scale
        let image = NSImage(size: NSSize(width: pixels, height: pixels))
        image.lockFocus()
        let s = CGFloat(pixels)
        let tile = NSBezierPath(roundedRect: NSRect(x: s*0.06, y: s*0.06, width: s*0.88, height: s*0.88), xRadius: s*0.20, yRadius: s*0.20)
        NSGradient(starting: NSColor(calibratedRed: 0.08, green: 0.25, blue: 0.63, alpha: 1), ending: NSColor(calibratedRed: 0.08, green: 0.67, blue: 0.82, alpha: 1))!.draw(in: tile, angle: 50)
        for x in [0.37, 0.63] {
            for y in [0.37, 0.63] {
                NSColor.white.withAlphaComponent(0.95).setFill()
                NSBezierPath(ovalIn: NSRect(x: s*CGFloat(x)-s*0.095, y: s*CGFloat(y)-s*0.095, width: s*0.19, height: s*0.19)).fill()
            }
        }
        image.unlockFocus()
        let bitmap = NSBitmapImageRep(data: image.tiffRepresentation!)!
        let data = bitmap.representation(using: .png, properties: [:])!
        let name = "icon_\(size)x\(size)\(scale == 2 ? "@2x" : "").png"
        try data.write(to: directory.appendingPathComponent(name))
    }
}
