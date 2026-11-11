import ApplicationServices
import Foundation

let processID = pid_t(Int32(CommandLine.arguments[1])!)
let app = AXUIElementCreateApplication(processID)
func attribute(_ element: AXUIElement, _ name: String) -> CFTypeRef? {
    var value: CFTypeRef?
    return AXUIElementCopyAttributeValue(element, name as CFString, &value) == .success ? value : nil
}
func string(_ element: AXUIElement, _ name: String) -> String {
    guard let value = attribute(element, name) else { return "" }
    return String(describing: value)
}
func find(_ role: String, _ expected: String) -> AXUIElement? {
    var visited = 0
    func walk(_ element: AXUIElement, _ depth: Int) -> AXUIElement? {
        if depth > 25 || visited >= 2500 { return nil }
        visited += 1
        let nodeRole = string(element, kAXRoleAttribute as String)
        let name = string(element, kAXTitleAttribute as String)
        let detail = string(element, kAXDescriptionAttribute as String)
        let value = string(element, kAXValueAttribute as String)
        if nodeRole == role && (name == expected || detail == expected || value == expected) { return element }
        for child in (attribute(element, kAXChildrenAttribute as String) as? [AXUIElement] ?? []) {
            if let match = walk(child, depth + 1) { return match }
        }
        return nil
    }
    for window in (attribute(app, kAXWindowsAttribute as String) as? [AXUIElement] ?? []) {
        if let match = walk(window, 0) { return match }
    }
    return nil
}
func waitFor(_ role: String, _ name: String) -> AXUIElement? {
    for _ in 0..<30 {
        if let node = find(role, name) { return node }
        usleep(500_000)
    }
    return nil
}
func require(_ condition: @autoclosure () -> Bool, _ message: String) {
    if !condition() { fputs("ERROR: \(message)\n", stderr); exit(1) }
}
func press(_ name: String) {
    guard let node = waitFor("AXButton", name) else { require(false, "Button missing: \(name)"); return }
    require(AXUIElementPerformAction(node, kAXPressAction as CFString) == .success, "Could not press: \(name)")
}
if let button = find("AXButton", "关闭教程") {
    require(AXUIElementPerformAction(button, kAXPressAction as CFString) == .success, "Could not close tutorial")
}
require(waitFor("AXHeading", "向你的文件提问") != nil, "Ask heading missing")
press("搜索")
require(waitFor("AXHeading", "搜索你的文件") != nil, "Search heading missing")
press("文件")
require(waitFor("AXHeading", "已索引文件") != nil, "Files heading missing")
press("问答")
require(waitFor("AXHeading", "向你的文件提问") != nil, "Ask heading missing after return")
press("设置")
require(waitFor("AXButton", "关闭设置") != nil, "Settings close button missing")
press("关闭设置")
require(waitFor("AXHeading", "向你的文件提问") != nil, "Ask heading missing after closing settings")
let report: [String: Any] = ["status":"passed", "scope":"installed macOS app accessibility navigation and settings", "checks":["ask","search","files","settings open and close"]]
let data = try JSONSerialization.data(withJSONObject: report, options: [.sortedKeys])
print(String(decoding: data, as: UTF8.self))
