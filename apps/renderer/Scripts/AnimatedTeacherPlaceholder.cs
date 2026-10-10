using Godot;

namespace Govor.Renderer;

public partial class AnimatedTeacherPlaceholder : Node3D
{
    private Vector3 _origin;
    private StandardMaterial3D? _material;
    private string _sessionAction = "session_started";

    public override void _Ready()
    {
        _origin = Position;
        _material = new StandardMaterial3D
        {
            AlbedoColor = new Color(0.12f, 0.72f, 0.82f),
            Roughness = 0.38f,
        };
        var mesh = new MeshInstance3D
        {
            Name = "TeacherMesh",
            Mesh = new CapsuleMesh { Radius = 0.55f, Height = 2.3f },
            MaterialOverride = _material,
        };
        AddChild(mesh);
    }

    public override void _Process(double delta)
    {
        _ = delta;
        double phase = Time.GetTicksMsec() / 1000.0;
        float activity = _sessionAction switch
        {
            "teacher_speaking" => 1.6f,
            "recording" => 0.45f,
            "processing" => 0.8f,
            _ => 1.0f,
        };
        Position = _origin + Vector3.Up * (0.12f * activity * (float)Math.Sin(phase * 2.0));
        RotationDegrees = new Vector3(
            0.0f,
            (float)(phase * 24.0 * activity % 360.0),
            4.0f * (float)Math.Sin(phase));
    }

    public void ApplySessionAction(string action)
    {
        _sessionAction = action;
        if (_material is null)
        {
            return;
        }

        _material.AlbedoColor = action switch
        {
            "teacher_speaking" => new Color(0.12f, 0.82f, 0.92f),
            "recording" => new Color(0.95f, 0.48f, 0.28f),
            "processing" => new Color(0.72f, 0.45f, 0.92f),
            "reset" => new Color(0.12f, 0.72f, 0.82f),
            _ => new Color(0.18f, 0.68f, 0.76f),
        };
    }
}
