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
var nodes = [[String: String]]()
var visited = 0
func visit(_ element: AXUIElement, _ depth: Int) {
    if depth > 20 || visited >= 2000 { return }
    visited += 1
    let role = string(element, kAXRoleAttribute as String)
    let name = string(element, kAXTitleAttribute as String)
    let detail = string(element, kAXDescriptionAttribute as String)
    let value = string(element, kAXValueAttribute as String)
    if !name.isEmpty || !detail.isEmpty || !value.isEmpty {
        if nodes.count < 120 { nodes.append(["role": role, "name": name, "description": detail, "value": String(value.prefix(100))]) }
    }
    for child in (attribute(element, kAXChildrenAttribute as String) as? [AXUIElement] ?? []) { visit(child, depth + 1) }
}
for window in (attribute(app, kAXWindowsAttribute as String) as? [AXUIElement] ?? []) { visit(window, 0) }
let report: [String: Any] = ["visited": visited, "items": nodes]
let data = try JSONSerialization.data(withJSONObject: report, options: [.sortedKeys])
print(String(decoding: data, as: UTF8.self))
