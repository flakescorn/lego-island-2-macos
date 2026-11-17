import AppKit
import SwiftUI
import UniformTypeIdentifiers

private let upstream = URL(string: "https://github.com/AntAir267/li2-recompiled")!

struct PreparedGame: Codable {
    let schema: Int
    let source_version: String
    let game_path: String
    let executable_path: String
    let user_dir: String
    let input_name: String
    let game_version: String
    let preparation_log: String
}

final class LineReader: @unchecked Sendable {
    private let lock = NSLock()
    private var buffer = Data()
    func append(_ data: Data) -> [String] {
        lock.lock(); defer { lock.unlock() }
        buffer.append(data)
        var lines: [String] = []
        while let end = buffer.firstIndex(of: 10) {
            lines.append(String(decoding: buffer[..<end], as: UTF8.self))
            buffer.removeSubrange(...end)
        }
        return lines
    }
}

@MainActor
final class LauncherModel: ObservableObject {
    @Published var selected: URL?
    @Published var prepared: PreparedGame?
    @Published var busy = false
    @Published var playing = false
    @Published var stage = -1
    @Published var title = "Choose your copy of the game"
    @Published var detail = "Import your PC disc image. We’ll prepare it on this Mac."
    @Published var error: String?
    @Published var logs: [String] = []
    @Published var logURL: URL?
    @Published var toolsReady = false
    @Published var showAbout = false
    @Published var fullscreen = UserDefaults.standard.bool(forKey: "fullscreen") {
        didSet { UserDefaults.standard.set(fullscreen, forKey: "fullscreen") }
    }
    @Published var movies = UserDefaults.standard.object(forKey: "movies") as? Bool ?? true {
        didSet { UserDefaults.standard.set(movies, forKey: "movies") }
    }
    private var worker: Process?
    private var gameProcess: Process?
    private var cancelled = false
    let library: URL
    let source: URL
    let sourceVersion: String

    init() {
        let resources = Bundle.main.resourceURL!
        source = resources.appendingPathComponent("EngineSource", isDirectory: true)
        sourceVersion = (try? String(contentsOf: resources.appendingPathComponent("Source.version"), encoding: .utf8))?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        library = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("LEGOIsland2Mac", isDirectory: true)
        refreshTools()
        restore()
    }

    func refreshTools() {
        let p = Process(); p.executableURL = URL(fileURLWithPath: "/usr/bin/xcode-select")
        p.arguments = ["-p"]; p.standardOutput = FileHandle.nullDevice; p.standardError = FileHandle.nullDevice
        do { try p.run(); p.waitUntilExit(); toolsReady = p.terminationStatus == 0 }
        catch { toolsReady = false }
    }

    func installTools() {
        let p = Process(); p.executableURL = URL(fileURLWithPath: "/usr/bin/xcode-select")
        p.arguments = ["--install"]
        do { try p.run(); detail = "Complete Apple’s developer tools installer, then click Check Again." }
        catch { self.error = "Could not open Apple’s installer: \(error.localizedDescription)" }
    }

    func restore() {
        guard let data = try? Data(contentsOf: library.appendingPathComponent("prepared.json")),
              let game = try? JSONDecoder().decode(PreparedGame.self, from: data),
              game.schema == 1 else { return }
        if game.source_version != sourceVersion {
            detail = "This launcher has been updated. Choose your ISO again to prepare the new engine. Your saves are kept."
            return
        }
        guard FileManager.default.fileExists(atPath: game.executable_path),
              FileManager.default.fileExists(atPath: game.game_path) else {
            error = "Some prepared files have moved or are missing. Import your game again; your saves are kept."
            return
        }
        prepared = game; logURL = URL(fileURLWithPath: game.preparation_log)
        title = "Ready to return to the island"
        detail = "Your game is prepared locally. No disc image is needed to play this imported copy."
    }

    func choose(folder: Bool = false) {
        guard !busy && !playing else { return }
        let panel = NSOpenPanel()
        panel.title = folder ? "Choose an installed LEGO Island 2 folder" : "Choose your LEGO Island 2 PC ISO"
        panel.message = folder ? "The folder must contain LEGO Island 2.exe and _data." : "Use your own English Version 1 disc image. Your ISO stays unchanged."
        panel.canChooseDirectories = folder; panel.canChooseFiles = !folder
        panel.allowsMultipleSelection = false
        if !folder { panel.allowedContentTypes = [UTType(filenameExtension: "iso") ?? .data] }
        if panel.runModal() == .OK, let url = panel.url { select(url) }
    }

    func select(_ url: URL) {
        guard !busy && !playing else { return }
        var isDirectory: ObjCBool = false
        guard FileManager.default.fileExists(atPath: url.path, isDirectory: &isDirectory),
              isDirectory.boolValue || url.pathExtension.lowercased() == "iso" else {
            error = "Choose a PC ISO file, or an installed folder containing the executable and _data."
            return
        }
        selected = url; error = nil
        title = "Ready to prepare your game"
        detail = "First setup needs internet and several minutes. Your files stay on this Mac."
    }

    func prepare() {
        guard let selected, toolsReady, !busy, !playing else { return }
        busy = true; cancelled = false; error = nil; logs = []; stage = 0
        let p = Process(); worker = p
        p.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        p.arguments = ["-u", source.appendingPathComponent("tools/macos/launcher_backend.py").path,
                       "--source", source.path, "--input", selected.path, "--library", library.path]
        p.environment = ProcessInfo.processInfo.environment.filter { key, _ in
            !key.hasPrefix("LI2_") && !key.hasPrefix("DYLD_") && !key.hasPrefix("SDL_")
        }.merging(["PYTHONUNBUFFERED": "1", "PATH": "/usr/bin:/bin:/usr/sbin:/sbin"]) { _, new in new }
        let pipe = Pipe(); p.standardOutput = pipe; p.standardError = pipe
        let reader = LineReader()
        pipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            if data.isEmpty { handle.readabilityHandler = nil; return }
            for line in reader.append(data) {
                Task { @MainActor [weak self] in self?.consume(line) }
            }
        }
        p.terminationHandler = { [weak self] process in
            Task { @MainActor [weak self] in
                guard let self else { return }
                self.busy = false; self.worker = nil
                if self.cancelled {
                    self.title = "Preparation stopped"
                    self.detail = "Your original files and previous saves are unchanged. You can try again."
                } else if process.terminationStatus != 0 && self.error == nil {
                    self.error = "Preparation stopped unexpectedly. Open the log for details, then try again."
                }
            }
        }
        do { try p.run() }
        catch {
            busy = false; worker = nil
            self.error = "Could not start preparation: \(error.localizedDescription)"
        }
    }

    private func consume(_ line: String) {
        guard let data = line.data(using: .utf8),
              let event = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let type = event["type"] as? String else { appendLog(line); return }
        switch type {
        case "stage":
            stage = event["index"] as? Int ?? stage
            title = event["title"] as? String ?? title
            detail = event["detail"] as? String ?? detail
        case "log": appendLog(event["text"] as? String ?? "")
        case "logfile": if let path = event["path"] as? String { logURL = URL(fileURLWithPath: path) }
        case "error": error = event["message"] as? String ?? "Preparation failed."
        case "ready":
            selected = nil; restore()
        default: break
        }
    }

    private func appendLog(_ line: String) {
        logs.append(line)
        if logs.count > 150 { logs.removeFirst(logs.count - 150) }
    }

    func cancel() {
        guard let worker, worker.isRunning else { return }
        cancelled = true
        // The worker creates its own session; terminate it and its compiler children together.
        if kill(-worker.processIdentifier, SIGTERM) != 0 { worker.terminate() }
    }

    func play() {
        guard let prepared, !busy, !playing else { return }
        guard FileManager.default.fileExists(atPath: prepared.game_path),
              FileManager.default.fileExists(atPath: prepared.executable_path) else {
            error = "Your prepared game files are missing. Import your ISO again. Your saves are kept."
            return
        }
        do { try FileManager.default.createDirectory(at: URL(fileURLWithPath: prepared.user_dir), withIntermediateDirectories: true) }
        catch { self.error = "Could not open your save folder: \(error.localizedDescription)"; return }
        error = nil
        let p = Process(); gameProcess = p
        p.executableURL = URL(fileURLWithPath: prepared.executable_path)
        let log = URL(fileURLWithPath: prepared.user_dir).appendingPathComponent("last-run.log")
        p.arguments = ["--play", "--game", prepared.game_path, "--user", prepared.user_dir,
                       "--option", "display=\(fullscreen ? "fullscreen" : "window")",
                       "--option", "intro_movies=\(movies ? "on" : "off")", "--logfile", log.path]
        p.environment = ProcessInfo.processInfo.environment.filter { key, _ in
            !key.hasPrefix("LI2_") && !key.hasPrefix("DYLD_") && !key.hasPrefix("SDL_")
        }
        p.standardOutput = FileHandle.nullDevice; p.standardError = FileHandle.nullDevice
        p.terminationHandler = { [weak self] process in
            Task { @MainActor [weak self] in
                self?.playing = false; self?.gameProcess = nil
                if process.terminationStatus != 0 {
                    self?.logURL = log
                    self?.error = "The game exited with an error. Your progress is kept in the save folder; open the log for details."
                }
            }
        }
        do { try p.run(); playing = true }
        catch { gameProcess = nil; self.error = "Could not launch the game: \(error.localizedDescription)" }
    }

    func revealLibrary() {
        try? FileManager.default.createDirectory(at: library, withIntermediateDirectories: true)
        NSWorkspace.shared.open(library)
    }
    func revealSaves() {
        guard let prepared else { return }
        NSWorkspace.shared.open(URL(fileURLWithPath: prepared.user_dir))
    }
}

struct LauncherView: View {
    @ObservedObject var model: LauncherModel
    @State private var dropTarget = false
    @State private var showLog = false
    private let steps = ["Check game", "Set up engine", "Import files", "Prepare gameplay", "Startup check", "Finish"]
    var body: some View {
        HStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 22) {
                Image(systemName: "square.stack.3d.up.fill").font(.system(size: 38)).foregroundStyle(.blue)
                Text("LEGO Island 2\nfor macOS").font(.system(size: 25, weight: .bold, design: .rounded))
                Text("APPLE SILICON PREVIEW").font(.system(size: 9, weight: .semibold)).tracking(1.2).foregroundStyle(.secondary)
                Divider()
                Label("Your copy. Prepared locally.", systemImage: "internaldrive").font(.callout)
                Text("Original English Version 1\nPC disc image required.").font(.callout).foregroundStyle(.secondary)
                Spacer()
                Button("About & Credits") { model.showAbout = true }.buttonStyle(.plain).foregroundStyle(.secondary)
                Link("Based on li2-recompiled ↗", destination: upstream).font(.caption)
                Text("Unofficial fan project.\nNot affiliated with LEGO.").font(.caption2).foregroundStyle(.secondary)
            }.padding(26).frame(width: 220).frame(maxHeight: .infinity).background(.quaternary.opacity(0.45))
            VStack(alignment: .leading, spacing: 20) {
                HStack {
                    Text(model.prepared != nil && model.selected == nil ? "Your game" : "Welcome to the island")
                        .font(.system(size: 28, weight: .bold))
                    Spacer()
                    Text("PREVIEW 0.2").font(.caption2.weight(.semibold)).padding(.horizontal, 9).padding(.vertical, 5)
                        .background(.blue.opacity(0.09), in: Capsule()).foregroundStyle(.blue)
                }
                Text("Bring your original PC game. We’ll handle the Mac setup.").foregroundStyle(.secondary)
                if model.prepared != nil && model.selected == nil && !model.busy {
                    readyCard
                } else {
                    importCard
                }
                if !model.toolsReady && (model.prepared == nil || model.selected != nil) {
                    VStack(alignment: .leading, spacing: 9) {
                        Label("One-time setup: Apple’s developer tools", systemImage: "wrench.and.screwdriver")
                            .font(.headline)
                        Text("These provide the compiler used to prepare your game on your Mac. Full Xcode is not required.")
                            .font(.callout).foregroundStyle(.secondary)
                        HStack {
                            Button("Install Apple Tools") { model.installTools() }
                            Button("Check Again") { model.refreshTools() }
                        }
                    }.padding(16).frame(maxWidth: .infinity, alignment: .leading).background(.orange.opacity(0.07), in: RoundedRectangle(cornerRadius: 14))
                }
                VStack(alignment: .leading, spacing: 10) {
                    Text(model.title).font(.headline)
                    Text(model.detail).font(.callout).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
                    if model.busy {
                        ProgressView(value: Double(max(0, model.stage)), total: 6).tint(.blue)
                        HStack(spacing: 7) {
                            ForEach(Array(steps.enumerated()), id: \.offset) { index, name in
                                Text(name).font(.system(size: 9, weight: index == model.stage ? .bold : .regular))
                                    .foregroundStyle(index <= model.stage ? Color.blue : Color.secondary)
                                if index != steps.count - 1 { Spacer(minLength: 0) }
                            }
                        }
                    }
                }
                if let error = model.error {
                    Label(error, systemImage: "exclamationmark.circle.fill").font(.callout).foregroundStyle(.red)
                        .textSelection(.enabled).fixedSize(horizontal: false, vertical: true)
                }
                Spacer(minLength: 0)
                HStack {
                    if model.busy {
                        ProgressView().controlSize(.small)
                        Button("Stop Preparation") { model.cancel() }
                    } else if model.selected != nil {
                        Button("Prepare Game") { model.prepare() }.buttonStyle(.borderedProminent).controlSize(.large)
                            .disabled(!model.toolsReady)
                        if model.prepared != nil {
                            Button("Back to Game") { model.selected = nil; model.error = nil; model.restore() }
                        }
                    }
                    Spacer()
                    if model.logURL != nil { Button("Open Log") { if let url = model.logURL { NSWorkspace.shared.open(url) } } }
                    if !model.logs.isEmpty { Button(showLog ? "Hide Details" : "Show Details") { showLog.toggle() } }
                }
                if showLog {
                    ScrollView {
                        Text(model.logs.suffix(60).joined(separator: "\n"))
                            .font(.system(size: 10, design: .monospaced)).textSelection(.enabled)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }.frame(height: 100).padding(10).background(.quaternary.opacity(0.35), in: RoundedRectangle(cornerRadius: 8))
                }
                HStack {
                    Label("Game files never leave this Mac", systemImage: "lock.shield").font(.caption).foregroundStyle(.secondary)
                    Spacer()
                    Button("Open Library") { model.revealLibrary() }.font(.caption).buttonStyle(.plain).foregroundStyle(.secondary)
                }
            }.padding(30).frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        }
        .frame(minWidth: 900, minHeight: 630)
        .onReceive(NotificationCenter.default.publisher(for: NSApplication.didBecomeActiveNotification)) { _ in model.refreshTools() }
        .onReceive(NotificationCenter.default.publisher(for: NSApplication.willTerminateNotification)) { _ in model.cancel() }
        .sheet(isPresented: $model.showAbout) { about }
    }

    private var importCard: some View {
        VStack(spacing: 13) {
            Image(systemName: model.selected == nil ? "opticaldisc" : "checkmark.circle.fill")
                .font(.system(size: 38)).foregroundStyle(.blue)
            Text(model.selected?.lastPathComponent ?? "Drop your PC ISO here").font(.headline).lineLimit(2)
            Text(model.selected == nil ? "Your original disc image stays unchanged." : "Ready for local preparation.")
                .font(.callout).foregroundStyle(.secondary)
            HStack {
                Button("Choose ISO…") { model.choose() }.buttonStyle(.borderedProminent)
                Menu("Other options") {
                    Button("Choose Installed Game Folder…") { model.choose(folder: true) }
                }.menuStyle(.borderlessButton).fixedSize()
            }.disabled(model.busy || model.playing)
        }.padding(24).frame(maxWidth: .infinity)
            .background(dropTarget ? Color.blue.opacity(0.09) : Color.blue.opacity(0.035), in: RoundedRectangle(cornerRadius: 18))
            .overlay(RoundedRectangle(cornerRadius: 18).strokeBorder(.blue.opacity(0.25), style: StrokeStyle(lineWidth: 1.5, dash: [6, 5])))
            .onDrop(of: [UTType.fileURL.identifier], isTargeted: $dropTarget) { providers in
                guard !model.busy, !model.playing, let provider = providers.first else { return false }
                _ = provider.loadDataRepresentation(forTypeIdentifier: UTType.fileURL.identifier) { data, _ in
                    guard let data, let url = URL(dataRepresentation: data, relativeTo: nil) else { return }
                    Task { @MainActor in model.select(url) }
                }
                return true
            }
    }

    private var readyCard: some View {
        VStack(alignment: .leading, spacing: 17) {
            HStack(spacing: 14) {
                Image(systemName: "gamecontroller.fill").font(.system(size: 37)).foregroundStyle(.blue)
                VStack(alignment: .leading, spacing: 4) {
                    Text("LEGO Island 2").font(.title2.bold())
                    Text("English Version 1 · Native ARM64").font(.callout).foregroundStyle(.secondary)
                }
                Spacer()
                Button(model.playing ? "Game Running" : "Play") { model.play() }
                    .buttonStyle(.borderedProminent).controlSize(.large).disabled(model.playing)
                    .keyboardShortcut(.return, modifiers: [])
            }
            Divider()
            HStack(spacing: 22) {
                Toggle("Fullscreen", isOn: $model.fullscreen)
                Toggle("Startup movies", isOn: $model.movies)
            }.toggleStyle(.checkbox).disabled(model.playing)
            Text("Arrows: move   ·   Option: jump   ·   Return: select   ·   Esc: pause")
                .font(.caption).foregroundStyle(.secondary)
            HStack {
                Button("Save Folder") { model.revealSaves() }
                Spacer()
                Button("Import Another Copy…") { model.choose() }.disabled(model.playing)
            }.font(.callout)
        }.padding(22).background(.blue.opacity(0.045), in: RoundedRectangle(cornerRadius: 18))
    }

    private var about: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("LEGO Island 2 for macOS").font(.title2.bold())
            Text("An experimental, unofficial Apple Silicon port and local game launcher.")
            Text("Based on AntAir267’s li2-recompiled translator and runtime, with macOS and English Version 1 adaptations developed using AI assistance. Original game by Silicon Dreams / LEGO Media.")
                .foregroundStyle(.secondary)
            Link("Original project and author ↗", destination: upstream)
            Text("The launcher contains open-source tools only. Original game files and locally translated game code are never included in the public download. Initial town gameplay, save/load and Mac launch have been tested; a full playthrough has not.")
                .font(.callout)
            HStack {
                Button("Licenses & Credits") { NSWorkspace.shared.open(model.source.appendingPathComponent("THIRD_PARTY_NOTICES.md")) }
                Spacer()
                Button("Done") { model.showAbout = false }.keyboardShortcut(.defaultAction)
            }
        }.padding(30).frame(width: 520)
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        NSApp.activate(ignoringOtherApps: true)
    }
}

@main
struct IslandLauncherApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var delegate
    @StateObject private var model = LauncherModel()
    var body: some Scene {
        Window("LEGO Island 2 for macOS", id: "launcher") {
            LauncherView(model: model).onDisappear { model.cancel() }
        }.defaultSize(width: 960, height: 680).windowResizability(.contentMinSize)
        .commands {
            CommandGroup(replacing: .newItem) { Button("Import Game ISO…") { model.choose() }.disabled(model.busy || model.playing) }
            CommandGroup(replacing: .appInfo) { Button("About LEGO Island 2 for macOS") { model.showAbout = true } }
        }
    }
}
