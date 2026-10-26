using Godot;

namespace Govor.Renderer;

public sealed record TeacherProfileDefinition(
    string Id,
    string DisplayName,
    string VoiceDescription,
    string AssetPath);

/// <summary>Closed catalog shared by the host selector and the renderer avatar.</summary>
public static class TeacherProfileCatalog
{
    private const string PreferencesPath = "user://preferences.cfg";
    private const string PreferencesSection = "teacher";
    private const string PreferencesKey = "profile_id";

    public const string DefaultProfileId = "amira";

    public static IReadOnlyList<TeacherProfileDefinition> Profiles { get; } =
    [
        new("elena", "Elena", "Female voice", "res://Assets/Teacher/Ara/elena.glb"),
        new("amira", "Amira", "Female voice", "res://Assets/Teacher/Ara/amira.glb"),
        new("daniel", "Daniel", "Male voice", "res://Assets/Teacher/Ara/daniel.glb"),
    ];

    public static TeacherProfileDefinition Get(string profileId) =>
        Profiles.FirstOrDefault(profile => profile.Id == profileId) ??
        throw new InvalidDataException("Teacher profile is not allow-listed.");

    public static bool IsAllowed(string profileId) =>
        Profiles.Any(profile => profile.Id == profileId);

    public static string LoadPreference()
    {
        var config = new ConfigFile();
        if (config.Load(PreferencesPath) != Error.Ok)
        {
            return DefaultProfileId;
        }
        string profileId = config.GetValue(
            PreferencesSection,
            PreferencesKey,
            DefaultProfileId).AsString();
        return IsAllowed(profileId) ? profileId : DefaultProfileId;
    }

    public static void SavePreference(string profileId)
    {
        _ = Get(profileId);
        var config = new ConfigFile();
        config.Load(PreferencesPath);
        config.SetValue(PreferencesSection, PreferencesKey, profileId);
        Error result = config.Save(PreferencesPath);
        if (result != Error.Ok)
        {
            GD.PushWarning($"Unable to persist the teacher selection: {result}.");
        }
    }
}
