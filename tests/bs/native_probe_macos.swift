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
var closeButton: AXUIElement?
func visit(_ element: AXUIElement, _ depth: Int) {
    if depth > 20 || visited >= 2000 { return }
    visited += 1
    let role = string(element, kAXRoleAttribute as String)
    let name = string(element, kAXTitleAttribute as String)
    let detail = string(element, kAXDescriptionAttribute as String)
    let value = string(element, kAXValueAttribute as String)
    if role == "AXButton" && (name == "关闭教程" || detail == "关闭教程") { closeButton = element }
    if !name.isEmpty || !detail.isEmpty || !value.isEmpty {
        if nodes.count < 120 { nodes.append(["role": role, "name": name, "description": detail, "value": String(value.prefix(100))]) }
    }
    for child in (attribute(element, kAXChildrenAttribute as String) as? [AXUIElement] ?? []) { visit(child, depth + 1) }
}
for window in (attribute(app, kAXWindowsAttribute as String) as? [AXUIElement] ?? []) { visit(window, 0) }
let initial = nodes
var pressed = -999
if let button = closeButton {
    pressed = Int(AXUIElementPerformAction(button, kAXPressAction as CFString).rawValue)
    sleep(2)
    nodes.removeAll()
    visited = 0
    for window in (attribute(app, kAXWindowsAttribute as String) as? [AXUIElement] ?? []) { visit(window, 0) }
}
let report: [String: Any] = ["visited": visited, "close_action": pressed, "initial": initial, "items": nodes]
let data = try JSONSerialization.data(withJSONObject: report, options: [.sortedKeys])
print(String(decoding: data, as: UTF8.self))
