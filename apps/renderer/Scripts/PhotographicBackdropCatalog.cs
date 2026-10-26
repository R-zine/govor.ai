using Godot;

namespace Govor.Renderer;

/// <summary>
/// Closed catalog of audited, application-owned photographic scene backdrops.
/// Environment IDs from the wire never become resource paths.
/// </summary>
internal static class PhotographicBackdropCatalog
{
    private const float BackdropHeight = 5.6f;
    private static readonly IReadOnlyDictionary<string, string> BackdropPaths =
        new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["cafe"] = "res://Assets/Backdrops/cafe.jpg",
            ["supermarket"] = "res://Assets/Backdrops/supermarket.jpg",
            ["airport"] = "res://Assets/Backdrops/airport.jpg",
            ["home"] = "res://Assets/Backdrops/home.jpg",
        };
    private static readonly Dictionary<string, Texture2D> TextureCache =
        new(StringComparer.Ordinal);
    private static readonly Dictionary<string, StandardMaterial3D> MaterialCache =
        new(StringComparer.Ordinal);

    public static int BackdropCount => BackdropPaths.Count;
    public static int CachedResourceCount => TextureCache.Count + MaterialCache.Count;

    public static bool HasBackdrop(string environmentId) =>
        BackdropPaths.ContainsKey(environmentId);

    public static Node3D Create(string environmentId)
    {
        if (!BackdropPaths.TryGetValue(environmentId, out string? path))
        {
            throw new ArgumentException("Unknown photographic backdrop ID.", nameof(environmentId));
        }

        if (!TextureCache.TryGetValue(environmentId, out Texture2D? texture))
        {
            texture = GD.Load<Texture2D>(path) ??
                throw new FileNotFoundException($"Unable to load backdrop {environmentId}.");
            TextureCache[environmentId] = texture;
        }
        if (!MaterialCache.TryGetValue(environmentId, out StandardMaterial3D? material))
        {
            material = new StandardMaterial3D
            {
                ResourceName = $"Backdrop-{environmentId}",
                AlbedoTexture = texture,
                AlbedoColor = new Color(0.82f, 0.82f, 0.82f, 1.0f),
                ShadingMode = BaseMaterial3D.ShadingModeEnum.Unshaded,
                CullMode = BaseMaterial3D.CullModeEnum.Disabled,
            };
            MaterialCache[environmentId] = material;
        }

        float aspect = texture.GetHeight() > 0
            ? texture.GetWidth() / (float)texture.GetHeight()
            : 16.0f / 9.0f;
        var root = new Node3D { Name = $"PhotographicBackdrop-{environmentId}" };
        root.AddChild(new MeshInstance3D
        {
            Name = "BackdropImage",
            Mesh = new QuadMesh { Size = new Vector2(BackdropHeight * aspect, BackdropHeight) },
            MaterialOverride = material,
            Position = new Vector3(0, 2.15f, -3.0f),
            CastShadow = GeometryInstance3D.ShadowCastingSetting.Off,
        });
        return root;
    }
}
