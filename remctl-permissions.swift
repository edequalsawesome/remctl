import AppKit
import Foundation

struct PermissionTarget {
    let title: String
    let path: String
    let subtitle: String
}

struct AfterCommand {
    let title: String
    let command: String
}

struct Options {
    var title = "RemCTL Permissions"
    var subtitle = "Grant Full Disk Access to the processes RemCTL uses."
    var autoOpenSettings = true
    var targets: [PermissionTarget] = []
    var afterCommands: [AfterCommand] = []
}

let fullDiskAccessURLs = [
    "x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension?Privacy_AllFiles",
    "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles",
]

func parseOptions() -> Options {
    var options = Options()
    let args = Array(CommandLine.arguments.dropFirst())
    var index = 0
    while index < args.count {
        switch args[index] {
        case "--title" where index + 1 < args.count:
            options.title = args[index + 1]
            index += 2
        case "--subtitle" where index + 1 < args.count:
            options.subtitle = args[index + 1]
            index += 2
        case "--target" where index + 3 < args.count:
            options.targets.append(PermissionTarget(title: args[index + 1], path: args[index + 2], subtitle: args[index + 3]))
            index += 4
        case "--after" where index + 2 < args.count:
            options.afterCommands.append(AfterCommand(title: args[index + 1], command: args[index + 2]))
            index += 3
        case "--no-open":
            options.autoOpenSettings = false
            index += 1
        default:
            index += 1
        }
    }
    if options.targets.isEmpty {
        options.targets.append(PermissionTarget(
            title: "Current Python interpreter",
            path: "/usr/bin/python3",
            subtitle: "Fallback target for direct CLI reads."
        ))
    }
    return options
}

func copyPath(_ path: String) {
    let pasteboard = NSPasteboard.general
    pasteboard.clearContents()
    pasteboard.setString(path, forType: .string)
    pasteboard.setString(URL(fileURLWithPath: path).absoluteString, forType: .fileURL)
}

func openFullDiskAccessSettings() {
    for rawURL in fullDiskAccessURLs {
        guard let url = URL(string: rawURL) else { continue }
        if NSWorkspace.shared.open(url) {
            return
        }
    }
}

func revealInFinder(_ path: String) {
    NSWorkspace.shared.selectFile(path, inFileViewerRootedAtPath: "")
}

final class ClosureTarget: NSObject {
    let closure: () -> Void

    init(_ closure: @escaping () -> Void) {
        self.closure = closure
    }

    @objc func invoke() {
        closure()
    }
}

func label(_ text: String, font: NSFont, color: NSColor = .labelColor, lines: Int = 0) -> NSTextField {
    let field = NSTextField(labelWithString: text)
    field.font = font
    field.textColor = color
    field.lineBreakMode = .byWordWrapping
    field.maximumNumberOfLines = lines
    field.translatesAutoresizingMaskIntoConstraints = false
    return field
}

final class TargetRowView: NSView, NSDraggingSource {
    private let target: PermissionTarget
    private var actions: [ClosureTarget] = []

    init(target: PermissionTarget, onLog: @escaping (String) -> Void) {
        self.target = target
        super.init(frame: .zero)
        translatesAutoresizingMaskIntoConstraints = false
        wantsLayer = true
        layer?.cornerRadius = 10
        layer?.borderWidth = 1
        layer?.borderColor = NSColor.separatorColor.cgColor
        layer?.backgroundColor = NSColor.controlBackgroundColor.cgColor

        let icon = NSImageView(image: NSWorkspace.shared.icon(forFile: target.path))
        icon.translatesAutoresizingMaskIntoConstraints = false
        icon.imageScaling = .scaleProportionallyUpOrDown

        let titleField = label(target.title, font: .boldSystemFont(ofSize: 14), lines: 1)
        let subtitleField = label(target.subtitle, font: .systemFont(ofSize: 12), color: .secondaryLabelColor, lines: 2)
        let pathField = label(target.path, font: .monospacedSystemFont(ofSize: 11, weight: .regular), color: .tertiaryLabelColor, lines: 1)
        pathField.lineBreakMode = .byTruncatingMiddle

        let textStack = NSStackView(views: [titleField, subtitleField, pathField])
        textStack.orientation = .vertical
        textStack.spacing = 3
        textStack.alignment = .leading
        textStack.translatesAutoresizingMaskIntoConstraints = false

        let copyAction = ClosureTarget { [target] in
            copyPath(target.path)
            onLog("Copied: \(target.path)")
        }
        let copyButton = NSButton(title: "Copy Path", target: copyAction, action: #selector(ClosureTarget.invoke))
        copyButton.bezelStyle = .rounded

        let revealAction = ClosureTarget { [target] in
            revealInFinder(target.path)
            onLog("Revealed in Finder: \(target.path)")
        }
        let revealButton = NSButton(title: "Reveal", target: revealAction, action: #selector(ClosureTarget.invoke))
        revealButton.bezelStyle = .rounded
        actions.append(contentsOf: [copyAction, revealAction])

        let buttonStack = NSStackView(views: [copyButton, revealButton])
        buttonStack.orientation = .horizontal
        buttonStack.spacing = 8
        buttonStack.translatesAutoresizingMaskIntoConstraints = false

        addSubview(icon)
        addSubview(textStack)
        addSubview(buttonStack)

        NSLayoutConstraint.activate([
            heightAnchor.constraint(greaterThanOrEqualToConstant: 92),
            icon.leadingAnchor.constraint(equalTo: leadingAnchor, constant: 14),
            icon.centerYAnchor.constraint(equalTo: centerYAnchor),
            icon.widthAnchor.constraint(equalToConstant: 38),
            icon.heightAnchor.constraint(equalToConstant: 38),

            textStack.leadingAnchor.constraint(equalTo: icon.trailingAnchor, constant: 12),
            textStack.centerYAnchor.constraint(equalTo: centerYAnchor),
            textStack.trailingAnchor.constraint(lessThanOrEqualTo: buttonStack.leadingAnchor, constant: -12),

            buttonStack.trailingAnchor.constraint(equalTo: trailingAnchor, constant: -14),
            buttonStack.centerYAnchor.constraint(equalTo: centerYAnchor),
        ])

        toolTip = "Drag this row into Full Disk Access, or copy the path and use Command-Shift-G."
    }

    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    override func mouseDown(with event: NSEvent) {
        copyPath(target.path)
        let url = NSURL(fileURLWithPath: target.path)
        let item = NSDraggingItem(pasteboardWriter: url)
        let dragImage = NSWorkspace.shared.icon(forFile: target.path)
        dragImage.size = NSSize(width: 64, height: 64)
        item.setDraggingFrame(NSRect(x: 0, y: 0, width: 64, height: 64), contents: dragImage)
        beginDraggingSession(with: [item], event: event, source: self)
    }

    func draggingSession(_ session: NSDraggingSession, sourceOperationMaskFor context: NSDraggingContext) -> NSDragOperation {
        return .copy
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    private let options: Options
    private var window: NSWindow?
    private var actions: [ClosureTarget] = []
    private let outputView = NSTextView()

    init(options: Options) {
        self.options = options
    }

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        buildWindow()
        if options.autoOpenSettings {
            openFullDiskAccessSettings()
            log("Opened System Settings > Privacy & Security > Full Disk Access.")
        }
        if let first = options.targets.first {
            copyPath(first.path)
            log("Copied first target. In the file picker press Command-Shift-G, paste, press Return, then click Open.")
        }
        NSApp.activate(ignoringOtherApps: true)
    }

    private func buildWindow() {
        let content = NSView()
        content.translatesAutoresizingMaskIntoConstraints = false

        let titleField = label(options.title, font: .boldSystemFont(ofSize: 24), lines: 1)
        let subtitleField = label(options.subtitle, font: .systemFont(ofSize: 14), color: .secondaryLabelColor, lines: 2)

        let instructions = label(
            "1. Click Open Full Disk Access. 2. Click + in System Settings. 3. Drag a target row into the picker, or press Command-Shift-G and paste the copied path. 4. Restart/check RemCTL.",
            font: .systemFont(ofSize: 13),
            color: .secondaryLabelColor,
            lines: 3
        )

        let openAction = ClosureTarget {
            openFullDiskAccessSettings()
            self.log("Opened Full Disk Access settings.")
        }
        let openButton = NSButton(title: "Open Full Disk Access", target: openAction, action: #selector(ClosureTarget.invoke))
        openButton.bezelStyle = .rounded
        openButton.keyEquivalent = "\r"
        actions.append(openAction)

        let quitAction = ClosureTarget {
            NSApp.terminate(nil)
        }
        let quitButton = NSButton(title: "Done", target: quitAction, action: #selector(ClosureTarget.invoke))
        quitButton.bezelStyle = .rounded
        actions.append(quitAction)

        let topButtons = NSStackView(views: [openButton, quitButton])
        topButtons.orientation = .horizontal
        topButtons.spacing = 8
        topButtons.alignment = .trailing

        let header = NSStackView(views: [titleField, subtitleField, instructions, topButtons])
        header.orientation = .vertical
        header.spacing = 8
        header.alignment = .leading

        let targetRows = options.targets.map { target in
            TargetRowView(target: target) { [weak self] message in
                self?.log(message)
            }
        }
        let targetsStack = NSStackView(views: targetRows)
        targetsStack.orientation = .vertical
        targetsStack.spacing = 10
        targetsStack.alignment = .width

        outputView.isEditable = false
        outputView.font = .monospacedSystemFont(ofSize: 11, weight: .regular)
        outputView.textColor = .secondaryLabelColor
        outputView.backgroundColor = .textBackgroundColor
        let outputScroll = NSScrollView()
        outputScroll.hasVerticalScroller = true
        outputScroll.documentView = outputView
        outputScroll.translatesAutoresizingMaskIntoConstraints = false
        outputScroll.heightAnchor.constraint(equalToConstant: 104).isActive = true

        let commandButtons = options.afterCommands.map { command in
            let action = ClosureTarget { [weak self] in
                self?.runCommand(command)
            }
            let button = NSButton(title: command.title, target: action, action: #selector(ClosureTarget.invoke))
            button.bezelStyle = .rounded
            actions.append(action)
            return button
        }
        let commandsStack = NSStackView(views: commandButtons)
        commandsStack.orientation = .horizontal
        commandsStack.spacing = 8
        commandsStack.alignment = .leading

        let mainStack = NSStackView(views: [header, targetsStack, commandsStack, outputScroll])
        mainStack.orientation = .vertical
        mainStack.spacing = 16
        mainStack.alignment = .width
        mainStack.translatesAutoresizingMaskIntoConstraints = false
        content.addSubview(mainStack)

        NSLayoutConstraint.activate([
            mainStack.leadingAnchor.constraint(equalTo: content.leadingAnchor, constant: 22),
            mainStack.trailingAnchor.constraint(equalTo: content.trailingAnchor, constant: -22),
            mainStack.topAnchor.constraint(equalTo: content.topAnchor, constant: 22),
            mainStack.bottomAnchor.constraint(equalTo: content.bottomAnchor, constant: -22),
        ])

        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 760, height: 620),
            styleMask: [.titled, .closable, .miniaturizable],
            backing: .buffered,
            defer: false
        )
        window.title = "RemCTL Permissions"
        window.contentView = content
        window.level = .floating
        window.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        window.center()
        window.makeKeyAndOrderFront(nil)
        self.window = window
    }

    private func log(_ text: String) {
        let existing = outputView.string
        outputView.string = existing.isEmpty ? text : "\(existing)\n\(text)"
        outputView.scrollToEndOfDocument(nil)
    }

    private func runCommand(_ command: AfterCommand) {
        log("$ \(command.command)")
        DispatchQueue.global(qos: .userInitiated).async {
            let process = Process()
            process.executableURL = URL(fileURLWithPath: "/bin/zsh")
            process.arguments = ["-lc", command.command]
            let pipe = Pipe()
            process.standardOutput = pipe
            process.standardError = pipe
            do {
                try process.run()
                process.waitUntilExit()
                let data = pipe.fileHandleForReading.readDataToEndOfFile()
                let output = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
                DispatchQueue.main.async {
                    if !output.isEmpty {
                        self.log(output)
                    }
                    self.log(process.terminationStatus == 0 ? "Command completed." : "Command failed with exit \(process.terminationStatus).")
                }
            } catch {
                DispatchQueue.main.async {
                    self.log("Could not run command: \(error.localizedDescription)")
                }
            }
        }
    }
}

let app = NSApplication.shared
let delegate = AppDelegate(options: parseOptions())
app.delegate = delegate
app.run()
