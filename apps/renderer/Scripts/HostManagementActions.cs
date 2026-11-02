using System.Diagnostics;

namespace Govor.Renderer;

/// <summary>Closed local-only entry points surfaced by the host pre-connect UI.</summary>
public static class HostManagementActions
{
    public const int ApplyApplicationPatchExitCode = 42;

    private static readonly HashSet<string> InteractiveCommands =
    [
        "Create-Lesson.cmd",
        "Manage-Lessons.cmd",
        "Manage-Environments.cmd",
        "Apply-Govor-Patch.cmd",
    ];

    public static string ResolveCommand(string installRoot, string commandName)
    {
        if (string.IsNullOrWhiteSpace(installRoot) || !InteractiveCommands.Contains(commandName))
        {
            throw new InvalidDataException("Host management command is not allow-listed.");
        }
        string root = Path.TrimEndingDirectorySeparator(Path.GetFullPath(installRoot));
        string candidate = Path.GetFullPath(Path.Combine(root, commandName));
        if (!string.Equals(Path.GetDirectoryName(candidate), root, StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidDataException("Host management command left the install directory.");
        }
        return candidate;
    }

    public static bool IsAvailable(string installRoot, string commandName) =>
        File.Exists(ResolveCommand(installRoot, commandName));

    public static void Launch(string installRoot, string commandName)
    {
        string command = ResolveCommand(installRoot, commandName);
        if (!File.Exists(command))
        {
            throw new FileNotFoundException("The installed host management command is missing.", command);
        }
        Process.Start(new ProcessStartInfo
        {
            FileName = command,
            WorkingDirectory = Path.GetFullPath(installRoot),
            UseShellExecute = true,
        });
    }
}
