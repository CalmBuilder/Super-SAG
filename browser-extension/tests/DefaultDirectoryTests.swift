import Foundation

@main
struct DefaultDirectoryTests {
    static func main() throws {
        let home = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: home, withIntermediateDirectories: true)
        defer { do { try FileManager.default.removeItem(at: home) } catch { fatalError("Cleanup failed: \(error)") } }
        let expected = home.appendingPathComponent("Documents/super-sag/clippings", isDirectory: true)
        let legacy = home.appendingPathComponent("Documents/sag-wiki/clippings", isDirectory: true)
        precondition(ClipFileStore.defaultDirectory(home: home) == expected)
        try FileManager.default.createDirectory(at: legacy, withIntermediateDirectories: true)
        let original = legacy.appendingPathComponent("original.md")
        try "original".write(to: original, atomically: true, encoding: .utf8)
        precondition(ClipFileStore.defaultDirectory(home: home) == legacy)
        try FileManager.default.createDirectory(at: expected, withIntermediateDirectories: true)
        precondition(ClipFileStore.defaultDirectory(home: home) == expected)
        let filename = "super-sag-default-save-test-\(UUID().uuidString).md"
        let content = "# Default folder save test\n"
        let file = try ClipFileStore.save(folder: "", filename: filename, content: content, downloads: expected)
        let saved = try String(contentsOf: file, encoding: .utf8)
        let preserved = try String(contentsOf: original, encoding: .utf8)
        precondition(saved == content)
        precondition(preserved == "original")
        precondition(!ClipFileStore.defaultDirectory.path.contains("/Library/Containers/"))
        print("Safari default folder: new and legacy locations verified in an isolated directory.")
    }
}
