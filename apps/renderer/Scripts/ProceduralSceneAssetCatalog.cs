using Godot;
using Govor.Contracts;

namespace Govor.Renderer;

/// <summary>Closed, process-local catalog. Unknown IDs become one predictable visual fallback.</summary>
internal static class ProceduralSceneAssetCatalog
{
    private static readonly Dictionary<string, Mesh> MeshCache = new(StringComparer.Ordinal);
    private static readonly Dictionary<string, StandardMaterial3D> MaterialCache = new(StringComparer.Ordinal);

    public static int CachedResourceCount => MeshCache.Count + MaterialCache.Count;

    public static Node3D Create(string assetId, out bool usedFallback)
    {
        usedFallback = false;
        Node3D? node = assetId switch
        {
            "cafe-counter" => Counter(assetId, new Color(0.38f, 0.19f, 0.09f)),
            "cafe-table" => Table(assetId, new Color(0.44f, 0.24f, 0.12f)),
            "cafe-chair" => Chair(assetId, new Color(0.33f, 0.16f, 0.08f)),
            "cafe-cup" => Cup(assetId),
            "market-shelf" => Shelf(assetId),
            "market-basket" => Basket(assetId),
            "market-crate" => Crate(assetId),
            "airport-counter" => Counter(assetId, new Color(0.23f, 0.34f, 0.48f)),
            "airport-sign" => Sign(assetId),
            "airport-bench" => Bench(assetId),
            "airport-suitcase" => Suitcase(assetId),
            "home-sofa" => Sofa(assetId),
            "home-table" => Table(assetId, new Color(0.35f, 0.21f, 0.13f)),
            "home-lamp" => Lamp(assetId),
            "home-bookshelf" => Bookshelf(assetId),
            _ => null,
        };
        if (node is not null)
        {
            return node;
        }

        usedFallback = true;
        var fallback = new Node3D { Name = "VisualFallback" };
        fallback.AddChild(Box(
            "MissingAsset",
            new Vector3(0.8f, 0.8f, 0.8f),
            new Vector3(0, 0.4f, 0),
            "fallback-magenta",
            new Color(0.92f, 0.08f, 0.66f)));
        return fallback;
    }

    public static Node3D CreatePrimitive(PrimitivePayload primitive)
    {
        primitive.Validate();
        var size = new Vector3(
            (float)primitive.Size.X,
            (float)primitive.Size.Y,
            (float)primitive.Size.Z);
        Color color = Color.FromHtml(primitive.Color);
        string key = $"custom-{primitive.Shape}-{primitive.Color}";
        Node3D geometry = primitive.Shape switch
        {
            "box" => Box("Primitive", size, Vector3.Zero, key, color),
            "cylinder" => Cylinder("Primitive", size.X / 2, size.Y, Vector3.Zero, key, color),
            "sphere" => Sphere("Primitive", size, Vector3.Zero, key, color),
            _ => throw new InvalidDataException("Unsupported scene primitive."),
        };
        var root = new Node3D { Name = "PrimitiveRoot" };
        root.AddChild(geometry);
        return root;
    }

    public static Node3D CreateEnvironment(string environmentId)
    {
        Color floor = environmentId switch
        {
            "cafe" => new Color(0.31f, 0.20f, 0.14f),
            "supermarket" => new Color(0.32f, 0.38f, 0.41f),
            "airport" => new Color(0.25f, 0.32f, 0.40f),
            "home" => new Color(0.36f, 0.27f, 0.22f),
            _ => new Color(0.18f, 0.18f, 0.2f),
        };
        Color wall = environmentId switch
        {
            "cafe" => new Color(0.48f, 0.29f, 0.19f),
            "supermarket" => new Color(0.72f, 0.77f, 0.73f),
            "airport" => new Color(0.54f, 0.65f, 0.76f),
            "home" => new Color(0.62f, 0.47f, 0.37f),
            _ => new Color(0.24f, 0.25f, 0.29f),
        };
        var root = new Node3D { Name = $"Environment-{environmentId}" };
        root.AddChild(Box("Floor", new Vector3(14, 0.12f, 12), new Vector3(0, -0.08f, 0), $"floor-{environmentId}", floor));
        root.AddChild(Box("BackWall", new Vector3(14, 6, 0.15f), new Vector3(0, 3, -3.2f), $"wall-{environmentId}", wall));
        root.AddChild(Box("LeftWall", new Vector3(0.15f, 6, 7), new Vector3(-6.9f, 3, 0.25f), $"wall-{environmentId}", wall.Darkened(0.12f)));
        return root;
    }

    private static Node3D Counter(string name, Color color)
    {
        var root = new Node3D { Name = name };
        root.AddChild(Box("Base", new Vector3(3.6f, 1.0f, 0.75f), new Vector3(0, 0.5f, 0), $"{name}-base", color));
        root.AddChild(Box("Top", new Vector3(3.9f, 0.12f, 0.95f), new Vector3(0, 1.05f, 0), $"{name}-top", color.Lightened(0.22f)));
        return root;
    }

    private static Node3D Table(string name, Color color)
    {
        var root = new Node3D { Name = name };
        root.AddChild(Cylinder("Top", 0.95f, 0.12f, new Vector3(0, 0.82f, 0), $"{name}-top", color));
        root.AddChild(Cylinder("Leg", 0.14f, 0.76f, new Vector3(0, 0.4f, 0), $"{name}-leg", color.Darkened(0.2f)));
        return root;
    }

    private static Node3D Chair(string name, Color color)
    {
        var root = new Node3D { Name = name };
        root.AddChild(Box("Seat", new Vector3(0.8f, 0.12f, 0.8f), new Vector3(0, 0.58f, 0), $"{name}-seat", color));
        root.AddChild(Box("Back", new Vector3(0.8f, 0.9f, 0.12f), new Vector3(0, 1.03f, -0.34f), $"{name}-back", color));
        foreach (float x in new[] { -0.31f, 0.31f })
        foreach (float z in new[] { -0.31f, 0.31f })
        {
            root.AddChild(Box("Leg", new Vector3(0.1f, 0.58f, 0.1f), new Vector3(x, 0.29f, z), $"{name}-leg", color.Darkened(0.2f)));
        }
        return root;
    }

    private static Node3D Cup(string name)
    {
        var root = new Node3D { Name = name };
        root.AddChild(Cylinder("Cup", 0.16f, 0.28f, new Vector3(0, 0.14f, 0), "ceramic", new Color(0.92f, 0.88f, 0.77f)));
        return root;
    }

    private static Node3D Shelf(string name)
    {
        var root = new Node3D { Name = name };
        Color frame = new(0.18f, 0.24f, 0.29f);
        root.AddChild(Box("Frame", new Vector3(2.2f, 2.7f, 0.55f), new Vector3(0, 1.35f, 0), $"{name}-frame", frame));
        for (int index = 0; index < 4; index++)
        {
            Color product = index % 2 == 0 ? new Color(0.88f, 0.48f, 0.18f) : new Color(0.2f, 0.7f, 0.42f);
            root.AddChild(Box($"Products{index}", new Vector3(1.85f, 0.34f, 0.61f), new Vector3(0, 0.42f + index * 0.62f, 0.02f), $"products-{index}", product));
        }
        return root;
    }

    private static Node3D Basket(string name) => SimpleBoxObject(name, new Vector3(0.9f, 0.45f, 0.65f), new Color(0.85f, 0.24f, 0.18f));
    private static Node3D Crate(string name) => SimpleBoxObject(name, new Vector3(1.05f, 0.7f, 0.85f), new Color(0.53f, 0.33f, 0.14f));

    private static Node3D Sign(string name)
    {
        var root = new Node3D { Name = name };
        root.AddChild(Box("Panel", new Vector3(2.5f, 0.8f, 0.14f), Vector3.Zero, "airport-sign-blue", new Color(0.08f, 0.33f, 0.63f)));
        root.AddChild(Box("Arrow", new Vector3(0.9f, 0.14f, 0.16f), new Vector3(0.45f, 0, 0.08f), "airport-sign-white", new Color(0.93f, 0.95f, 0.98f)));
        return root;
    }

    private static Node3D Bench(string name)
    {
        var root = new Node3D { Name = name };
        Color color = new(0.19f, 0.27f, 0.38f);
        root.AddChild(Box("Seat", new Vector3(2.6f, 0.18f, 0.72f), new Vector3(0, 0.55f, 0), $"{name}-seat", color));
        root.AddChild(Box("Back", new Vector3(2.6f, 0.78f, 0.16f), new Vector3(0, 0.98f, -0.3f), $"{name}-back", color.Lightened(0.1f)));
        return root;
    }

    private static Node3D Suitcase(string name)
    {
        var root = SimpleBoxObject(name, new Vector3(0.65f, 1.0f, 0.38f), new Color(0.52f, 0.16f, 0.21f));
        root.AddChild(Box("Handle", new Vector3(0.28f, 0.3f, 0.08f), new Vector3(0, 1.12f, 0), $"{name}-handle", new Color(0.08f, 0.09f, 0.11f)));
        return root;
    }

    private static Node3D Sofa(string name)
    {
        var root = new Node3D { Name = name };
        Color color = new(0.22f, 0.46f, 0.49f);
        root.AddChild(Box("Seat", new Vector3(2.8f, 0.55f, 1.05f), new Vector3(0, 0.42f, 0), $"{name}-seat", color));
        root.AddChild(Box("Back", new Vector3(2.8f, 1.1f, 0.35f), new Vector3(0, 1.02f, -0.43f), $"{name}-back", color.Lightened(0.08f)));
        return root;
    }

    private static Node3D Lamp(string name)
    {
        var root = new Node3D { Name = name };
        root.AddChild(Cylinder("Stand", 0.08f, 1.8f, new Vector3(0, 0.9f, 0), $"{name}-stand", new Color(0.18f, 0.16f, 0.14f)));
        root.AddChild(Sphere("Shade", new Vector3(0.7f, 0.45f, 0.7f), new Vector3(0, 1.9f, 0), $"{name}-shade", new Color(0.95f, 0.72f, 0.32f)));
        return root;
    }

    private static Node3D Bookshelf(string name)
    {
        var root = new Node3D { Name = name };
        Color wood = new(0.34f, 0.18f, 0.1f);
        root.AddChild(Box("Case", new Vector3(1.6f, 2.7f, 0.42f), new Vector3(0, 1.35f, 0), $"{name}-case", wood));
        for (int index = 0; index < 3; index++)
        {
            root.AddChild(Box($"Books{index}", new Vector3(1.28f, 0.42f, 0.48f), new Vector3(0, 0.5f + index * 0.78f, 0.04f), $"books-{index}", new Color(0.58f - index * 0.1f, 0.24f + index * 0.15f, 0.25f)));
        }
        return root;
    }

    private static Node3D SimpleBoxObject(string name, Vector3 size, Color color)
    {
        var root = new Node3D { Name = name };
        root.AddChild(Box("Body", size, new Vector3(0, size.Y / 2, 0), $"{name}-body", color));
        return root;
    }

    private static MeshInstance3D Box(string name, Vector3 size, Vector3 position, string key, Color color)
    {
        string meshKey = $"box:{size.X:F3}:{size.Y:F3}:{size.Z:F3}";
        if (!MeshCache.TryGetValue(meshKey, out Mesh? mesh))
        {
            mesh = new BoxMesh { Size = size };
            MeshCache[meshKey] = mesh;
        }
        return Part(name, mesh, position, key, color);
    }

    private static MeshInstance3D Cylinder(string name, float radius, float height, Vector3 position, string key, Color color)
    {
        string meshKey = $"cylinder:{radius:F3}:{height:F3}";
        if (!MeshCache.TryGetValue(meshKey, out Mesh? mesh))
        {
            mesh = new CylinderMesh { TopRadius = radius, BottomRadius = radius, Height = height };
            MeshCache[meshKey] = mesh;
        }
        return Part(name, mesh, position, key, color);
    }

    private static MeshInstance3D Sphere(string name, Vector3 scale, Vector3 position, string key, Color color)
    {
        const string meshKey = "sphere:unit";
        if (!MeshCache.TryGetValue(meshKey, out Mesh? mesh))
        {
            mesh = new SphereMesh { Radius = 0.5f, Height = 1.0f };
            MeshCache[meshKey] = mesh;
        }
        MeshInstance3D instance = Part(name, mesh, position, key, color);
        instance.Scale = scale;
        return instance;
    }

    private static MeshInstance3D Part(string name, Mesh mesh, Vector3 position, string key, Color color)
    {
        if (!MaterialCache.TryGetValue(key, out StandardMaterial3D? material))
        {
            material = new StandardMaterial3D { AlbedoColor = color, Roughness = 0.78f };
            MaterialCache[key] = material;
        }
        return new MeshInstance3D
        {
            Name = name,
            Mesh = mesh,
            Position = position,
            MaterialOverride = material,
        };
    }
}
