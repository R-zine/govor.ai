using Godot;

namespace Govor.Renderer;

/// <summary>
/// Displays a launcher-generated, short-lived pairing QR outside the captured media viewport.
/// The trusted startup argument contains only a local file path; pairing secrets never enter
/// renderer commands or process arguments.
/// </summary>
public partial class PairingQrOverlay : Control
{
    public string QrImagePath { get; set; } = string.Empty;

    public override void _Ready()
    {
        SetAnchorsAndOffsetsPreset(LayoutPreset.FullRect);
        ZIndex = 100;
        MouseFilter = MouseFilterEnum.Stop;

        var scrim = new ColorRect
        {
            Color = new Color(0.015f, 0.023f, 0.042f, 0.88f),
            MouseFilter = MouseFilterEnum.Stop,
        };
        scrim.SetAnchorsAndOffsetsPreset(LayoutPreset.FullRect);
        AddChild(scrim);

        var center = new CenterContainer();
        center.SetAnchorsAndOffsetsPreset(LayoutPreset.FullRect);
        AddChild(center);

        var panel = new PanelContainer
        {
            CustomMinimumSize = new Vector2(560.0f, 620.0f),
        };
        panel.AddThemeStyleboxOverride(
            "panel",
            new StyleBoxFlat
            {
                BgColor = new Color("f8fafc"),
                CornerRadiusTopLeft = 24,
                CornerRadiusTopRight = 24,
                CornerRadiusBottomLeft = 24,
                CornerRadiusBottomRight = 24,
                ContentMarginLeft = 36.0f,
                ContentMarginRight = 36.0f,
                ContentMarginTop = 28.0f,
                ContentMarginBottom = 28.0f,
            });
        center.AddChild(panel);

        var content = new VBoxContainer
        {
            Alignment = BoxContainer.AlignmentMode.Center,
        };
        content.AddThemeConstantOverride("separation", 12);
        panel.AddChild(content);
        var title = new Label
        {
            Text = "Connect your phone",
            HorizontalAlignment = HorizontalAlignment.Center,
        };
        title.AddThemeColorOverride("font_color", new Color("111827"));
        title.AddThemeFontSizeOverride("font_size", 30);
        content.AddChild(title);
        var instructions = new Label
        {
            Text = "Open govor.ai on Android and scan this QR code.",
            HorizontalAlignment = HorizontalAlignment.Center,
            AutowrapMode = TextServer.AutowrapMode.WordSmart,
            CustomMinimumSize = new Vector2(480.0f, 52.0f),
        };
        instructions.AddThemeColorOverride("font_color", new Color("4b5563"));
        instructions.AddThemeFontSizeOverride("font_size", 18);
        content.AddChild(instructions);

        TextureRect? qr = LoadQrTexture();
        if (qr is not null)
        {
            content.AddChild(qr);
        }
        else
        {
            var error = new Label
            {
                Text = "The QR image could not be loaded. Use manual pairing on the phone " +
                    "with the details in the host console.",
                HorizontalAlignment = HorizontalAlignment.Center,
                AutowrapMode = TextServer.AutowrapMode.WordSmart,
                CustomMinimumSize = new Vector2(480.0f, 320.0f),
            };
            error.AddThemeColorOverride("font_color", new Color("991b1b"));
            error.AddThemeFontSizeOverride("font_size", 18);
            content.AddChild(error);
        }

        var expiry = new Label
        {
            Text = "The code is one-time and expires after 10 minutes.",
            HorizontalAlignment = HorizontalAlignment.Center,
        };
        expiry.AddThemeColorOverride("font_color", new Color("4b5563"));
        expiry.AddThemeFontSizeOverride("font_size", 16);
        content.AddChild(expiry);
    }

    public void Dismiss()
    {
        Visible = false;
        MouseFilter = MouseFilterEnum.Ignore;
    }

    private TextureRect? LoadQrTexture()
    {
        if (string.IsNullOrWhiteSpace(QrImagePath) || !Godot.FileAccess.FileExists(QrImagePath))
        {
            GD.PushWarning("The launcher pairing QR image is unavailable.");
            return null;
        }

        using Image image = Image.LoadFromFile(QrImagePath);
        if (image.IsEmpty())
        {
            GD.PushWarning("The launcher pairing QR image is invalid.");
            return null;
        }

        return new TextureRect
        {
            Texture = ImageTexture.CreateFromImage(image),
            CustomMinimumSize = new Vector2(400.0f, 400.0f),
            ExpandMode = TextureRect.ExpandModeEnum.IgnoreSize,
            StretchMode = TextureRect.StretchModeEnum.KeepAspectCentered,
            MouseFilter = MouseFilterEnum.Ignore,
        };
    }
}
