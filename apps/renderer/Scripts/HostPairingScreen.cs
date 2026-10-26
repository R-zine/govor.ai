using Godot;

namespace Govor.Renderer;

/// <summary>
/// Owns the host's pre-lesson state. Pairing data comes from protected short-lived files whose
/// paths are supplied by the trusted launcher; secrets never enter process arguments or video.
/// </summary>
public partial class HostPairingScreen : Control
{
    private static readonly Color Background = new("0e1513");
    private static readonly Color Panel = new("17211e");
    private static readonly Color PanelRaised = new("202c28");
    private static readonly Color Primary = new("73dbc3");
    private static readonly Color OnPrimary = new("00382e");
    private static readonly Color Text = new("dee4e0");
    private static readonly Color MutedText = new("aebbb6");

    private Label? _expiryLabel;
    private Label? _statusLabel;
    private Control? _manualDialog;
    private MenuButton? _teacherMenu;
    private PairingBootstrapDetails? _details;
    private ulong _lastCountdownUpdateMs;

    public string QrImagePath { get; set; } = string.Empty;
    public string BootstrapPath { get; set; } = string.Empty;
    public bool ShowManualDetailsOnReady { get; set; }
    public string InitialTeacherProfileId { get; set; } = TeacherProfileCatalog.DefaultProfileId;
    public event Action<string>? TeacherProfileSelected;

    public override void _Ready()
    {
        SetAnchorsAndOffsetsPreset(LayoutPreset.FullRect);
        ZIndex = 100;
        MouseFilter = MouseFilterEnum.Stop;
        LoadDetails();

        var background = new ColorRect
        {
            Color = Background,
            MouseFilter = MouseFilterEnum.Stop,
        };
        background.SetAnchorsAndOffsetsPreset(LayoutPreset.FullRect);
        AddChild(background);

        var pageMargin = new MarginContainer();
        pageMargin.SetAnchorsAndOffsetsPreset(LayoutPreset.FullRect);
        pageMargin.AddThemeConstantOverride("margin_left", 58);
        pageMargin.AddThemeConstantOverride("margin_right", 58);
        pageMargin.AddThemeConstantOverride("margin_top", 34);
        pageMargin.AddThemeConstantOverride("margin_bottom", 34);
        AddChild(pageMargin);

        var page = new VBoxContainer
        {
            SizeFlagsHorizontal = SizeFlags.ExpandFill,
            SizeFlagsVertical = SizeFlags.ExpandFill,
        };
        page.AddThemeConstantOverride("separation", 24);
        pageMargin.AddChild(page);
        page.AddChild(CreateHeader());
        page.AddChild(CreateMainContent());

        _manualDialog = CreateManualDialog();
        _manualDialog.Visible = ShowManualDetailsOnReady;
        AddChild(_manualDialog);
        UpdateCountdown(force: true);
    }

    public override void _Process(double delta)
    {
        _ = delta;
        UpdateCountdown(force: false);
    }

    public void CompleteConnection()
    {
        Visible = false;
        MouseFilter = MouseFilterEnum.Ignore;
        SetProcess(false);
    }

    private Control CreateHeader()
    {
        var header = new HBoxContainer
        {
            CustomMinimumSize = new Vector2(0.0f, 54.0f),
        };
        header.AddThemeConstantOverride("separation", 14);

        Texture2D? iconTexture = GD.Load<Texture2D>("res://Assets/Brand/govor-icon.png");
        if (iconTexture is not null)
        {
            header.AddChild(new TextureRect
            {
                Texture = iconTexture,
                CustomMinimumSize = new Vector2(48.0f, 48.0f),
                ExpandMode = TextureRect.ExpandModeEnum.IgnoreSize,
                StretchMode = TextureRect.StretchModeEnum.KeepAspectCentered,
                MouseFilter = MouseFilterEnum.Ignore,
            });
        }

        var brand = new VBoxContainer();
        brand.AddThemeConstantOverride("separation", 0);
        brand.AddChild(StyledLabel("govor.ai", 24, Text, FontWeight.SemiBold));
        brand.AddChild(StyledLabel("Private local English tutor", 14, MutedText));
        header.AddChild(brand);
        header.AddChild(new Control { SizeFlagsHorizontal = SizeFlags.ExpandFill });
        header.AddChild(CreateTeacherMenu());

        var statusPanel = StyledPanel(PanelRaised, 18, 14, 10);
        _statusLabel = StyledLabel("Waiting for your phone", 15, Primary, FontWeight.SemiBold);
        statusPanel.AddChild(_statusLabel);
        header.AddChild(statusPanel);
        return header;
    }

    private Control CreateTeacherMenu()
    {
        string selectedId = TeacherProfileCatalog.IsAllowed(InitialTeacherProfileId)
            ? InitialTeacherProfileId
            : TeacherProfileCatalog.DefaultProfileId;
        TeacherProfileDefinition selected = TeacherProfileCatalog.Get(selectedId);
        _teacherMenu = new MenuButton
        {
            Text = $"Teacher · {selected.DisplayName}",
            TooltipText = "Choose the teacher model and matching voice",
            CustomMinimumSize = new Vector2(210.0f, 46.0f),
        };
        PopupMenu popup = _teacherMenu.GetPopup();
        for (int index = 0; index < TeacherProfileCatalog.Profiles.Count; index++)
        {
            TeacherProfileDefinition profile = TeacherProfileCatalog.Profiles[index];
            popup.AddRadioCheckItem(
                $"{profile.DisplayName} — {profile.VoiceDescription}",
                index);
            popup.SetItemChecked(index, profile.Id == selectedId);
        }
        popup.IdPressed += id => SelectTeacherProfile(checked((int)id));
        return _teacherMenu;
    }

    private void SelectTeacherProfile(int index)
    {
        if (index < 0 || index >= TeacherProfileCatalog.Profiles.Count || _teacherMenu is null)
        {
            return;
        }
        TeacherProfileDefinition selected = TeacherProfileCatalog.Profiles[index];
        PopupMenu popup = _teacherMenu.GetPopup();
        for (int item = 0; item < TeacherProfileCatalog.Profiles.Count; item++)
        {
            popup.SetItemChecked(item, item == index);
        }
        _teacherMenu.Text = $"Teacher · {selected.DisplayName}";
        TeacherProfileCatalog.SavePreference(selected.Id);
        TeacherProfileSelected?.Invoke(selected.Id);
    }

    private Control CreateMainContent()
    {
        var main = new HBoxContainer
        {
            SizeFlagsHorizontal = SizeFlags.ExpandFill,
            SizeFlagsVertical = SizeFlags.ExpandFill,
        };
        main.AddThemeConstantOverride("separation", 40);

        var instructions = new VBoxContainer
        {
            CustomMinimumSize = new Vector2(570.0f, 0.0f),
            SizeFlagsHorizontal = SizeFlags.ExpandFill,
            SizeFlagsVertical = SizeFlags.ExpandFill,
        };
        instructions.AddThemeConstantOverride("separation", 16);
        instructions.AddChild(StyledLabel("Connect your phone", 42, Text, FontWeight.Bold));
        instructions.AddChild(Paragraph(
            "Use your Android phone to connect securely. The 3D lesson starts only after you " +
            "choose a lesson on the phone.",
            19,
            MutedText,
            520.0f));
        instructions.AddChild(CreateStep(
            "1",
            "Open govor.ai on your phone",
            "Keep the phone and this PC on the same trusted private network."));
        instructions.AddChild(CreateStep(
            "2",
            "Tap \"Scan host QR\"",
            "Allow camera access when Android asks. The scan stays on your phone."));
        instructions.AddChild(CreateStep(
            "3",
            "Point the camera at the code",
            "Pairing and lesson loading continue automatically."));

        var manualButton = new Button
        {
            Text = "Manual pairing options",
            Disabled = _details is null,
            CustomMinimumSize = new Vector2(0.0f, 48.0f),
        };
        manualButton.Pressed += () =>
        {
            if (_manualDialog is not null)
            {
                _manualDialog.Visible = true;
            }
        };
        instructions.AddChild(manualButton);
        instructions.AddChild(Paragraph(
            "Trouble connecting? Disable VPNs and avoid guest or client-isolated Wi-Fi.",
            14,
            MutedText,
            520.0f));
        main.AddChild(instructions);
        main.AddChild(CreateQrCard());
        return main;
    }

    private Control CreateQrCard()
    {
        PanelContainer card = StyledPanel(Panel, 28, 26, 24);
        card.CustomMinimumSize = new Vector2(460.0f, 0.0f);
        card.SizeFlagsVertical = SizeFlags.ExpandFill;

        var content = new VBoxContainer
        {
            Alignment = BoxContainer.AlignmentMode.Center,
        };
        content.AddThemeConstantOverride("separation", 10);
        card.AddChild(content);
        content.AddChild(StyledLabel(
            "Scan to connect",
            25,
            Text,
            FontWeight.SemiBold,
            HorizontalAlignment.Center));
        content.AddChild(Paragraph(
            "One scan securely fills every connection detail.",
            15,
            MutedText,
            390.0f,
            HorizontalAlignment.Center));

        TextureRect? qr = LoadQrTexture();
        if (qr is not null)
        {
            var qrBackground = StyledPanel(new Color("ffffff"), 18, 16, 16);
            qrBackground.AddChild(qr);
            content.AddChild(qrBackground);
        }
        else
        {
            var error = StyledPanel(new Color("3d191d"), 18, 18, 18);
            error.CustomMinimumSize = new Vector2(360.0f, 330.0f);
            error.AddChild(Paragraph(
                "The QR code could not be loaded. Restart govor.ai or use the manual details " +
                "shown in the host console.",
                17,
                new Color("ffb4ab"),
                324.0f,
                HorizontalAlignment.Center));
            content.AddChild(error);
        }

        _expiryLabel = StyledLabel(
            "Checking pairing code...",
            15,
            MutedText,
            FontWeight.Normal,
            HorizontalAlignment.Center);
        content.AddChild(_expiryLabel);
        return card;
    }

    private Control CreateStep(string number, string title, string body)
    {
        var row = new HBoxContainer();
        row.AddThemeConstantOverride("separation", 14);
        var numberPanel = StyledPanel(Primary, 22, 10, 7);
        numberPanel.CustomMinimumSize = new Vector2(44.0f, 44.0f);
        numberPanel.AddChild(StyledLabel(
            number,
            18,
            OnPrimary,
            FontWeight.Bold,
            HorizontalAlignment.Center));
        row.AddChild(numberPanel);

        var copy = new VBoxContainer
        {
            SizeFlagsHorizontal = SizeFlags.ExpandFill,
        };
        copy.AddThemeConstantOverride("separation", 2);
        copy.AddChild(StyledLabel(title, 19, Text, FontWeight.SemiBold));
        copy.AddChild(Paragraph(body, 15, MutedText, 480.0f));
        row.AddChild(copy);
        return row;
    }

    private Control CreateManualDialog()
    {
        var layer = new Control
        {
            ZIndex = 10,
            MouseFilter = MouseFilterEnum.Stop,
        };
        layer.SetAnchorsAndOffsetsPreset(LayoutPreset.FullRect);
        var scrim = new ColorRect
        {
            Color = new Color(0.0f, 0.0f, 0.0f, 0.78f),
            MouseFilter = MouseFilterEnum.Stop,
        };
        scrim.SetAnchorsAndOffsetsPreset(LayoutPreset.FullRect);
        layer.AddChild(scrim);
        var center = new CenterContainer();
        center.SetAnchorsAndOffsetsPreset(LayoutPreset.FullRect);
        layer.AddChild(center);

        PanelContainer panel = StyledPanel(PanelRaised, 24, 30, 26);
        panel.CustomMinimumSize = new Vector2(800.0f, 560.0f);
        center.AddChild(panel);
        var content = new VBoxContainer();
        content.AddThemeConstantOverride("separation", 12);
        panel.AddChild(content);
        content.AddChild(StyledLabel("Manual pairing details", 30, Text, FontWeight.Bold));
        content.AddChild(Paragraph(
            "On the phone, open \"Pair manually\" and enter these values exactly. QR scanning is " +
            "recommended because the code and fingerprint are easy to mistype.",
            16,
            MutedText,
            730.0f));

        if (_details is not null)
        {
            AddManualDetail(content, "Media host", _details.MediaHost, 18);
            AddManualDetail(content, "Control host", _details.ControlHost, 18);
            AddManualDetail(content, "Pairing code", _details.PairingCode, 24);
            AddManualDetail(content, "Certificate SHA-256", _details.DisplayFingerprint(), 13);
        }
        else
        {
            content.AddChild(Paragraph(
                "Pairing details are unavailable. Restart govor.ai and check the host console.",
                17,
                new Color("ffb4ab"),
                730.0f));
        }

        content.AddChild(new Control { SizeFlagsVertical = SizeFlags.ExpandFill });
        var actions = new HBoxContainer();
        actions.AddThemeConstantOverride("separation", 12);
        var copy = new Button
        {
            Text = "Copy all details",
            Disabled = _details is null,
            CustomMinimumSize = new Vector2(220.0f, 48.0f),
        };
        copy.Pressed += CopyManualDetails;
        actions.AddChild(copy);
        actions.AddChild(new Control { SizeFlagsHorizontal = SizeFlags.ExpandFill });
        var close = new Button
        {
            Text = "Close",
            CustomMinimumSize = new Vector2(140.0f, 48.0f),
        };
        close.Pressed += () => layer.Visible = false;
        actions.AddChild(close);
        content.AddChild(actions);
        return layer;
    }

    private void AddManualDetail(VBoxContainer parent, string name, string value, int fontSize)
    {
        parent.AddChild(StyledLabel(name, 13, MutedText, FontWeight.SemiBold));
        var valuePanel = StyledPanel(Panel, 12, 14, 9);
        var label = new RichTextLabel
        {
            Text = value,
            FitContent = true,
            SelectionEnabled = true,
            AutowrapMode = TextServer.AutowrapMode.WordSmart,
            CustomMinimumSize = new Vector2(700.0f, 0.0f),
            MouseFilter = MouseFilterEnum.Stop,
        };
        label.AddThemeFontSizeOverride("normal_font_size", fontSize);
        label.AddThemeColorOverride("default_color", Text);
        valuePanel.AddChild(label);
        parent.AddChild(valuePanel);
    }

    private void CopyManualDetails()
    {
        if (_details is null)
        {
            return;
        }
        DisplayServer.ClipboardSet(
            $"Media host: {_details.MediaHost}\n" +
            $"Control host: {_details.ControlHost}\n" +
            $"Pairing code: {_details.PairingCode}\n" +
            $"Certificate SHA-256: {_details.CertificateSha256}");
        if (_statusLabel is not null)
        {
            _statusLabel.Text = "Pairing details copied";
        }
    }

    private void LoadDetails()
    {
        try
        {
            if (string.IsNullOrWhiteSpace(BootstrapPath))
            {
                throw new InvalidDataException("No pairing bootstrap path was supplied.");
            }
            var info = new FileInfo(BootstrapPath);
            if (!info.Exists || info.Length is < 1 or > 2_048)
            {
                throw new InvalidDataException("The pairing bootstrap file is unavailable.");
            }
            _details = PairingBootstrapDetails.Parse(System.IO.File.ReadAllText(BootstrapPath));
        }
        catch (Exception error) when (
            error is IOException or UnauthorizedAccessException or InvalidDataException or
            System.Text.Json.JsonException)
        {
            GD.PushWarning($"The pairing bootstrap details could not be loaded: {error.Message}");
        }
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
            CustomMinimumSize = new Vector2(328.0f, 328.0f),
            ExpandMode = TextureRect.ExpandModeEnum.IgnoreSize,
            StretchMode = TextureRect.StretchModeEnum.KeepAspectCentered,
            MouseFilter = MouseFilterEnum.Ignore,
        };
    }

    private void UpdateCountdown(bool force)
    {
        ulong nowMs = Time.GetTicksMsec();
        if (!force && nowMs - _lastCountdownUpdateMs < 500)
        {
            return;
        }
        _lastCountdownUpdateMs = nowMs;
        if (_expiryLabel is null || _details is null)
        {
            return;
        }

        long remaining = _details.ExpiresAtUnix - (long)Time.GetUnixTimeFromSystem();
        if (remaining <= 0)
        {
            _expiryLabel.Text = "Pairing code expired - restart govor.ai for a new code";
            _expiryLabel.AddThemeColorOverride("font_color", new Color("ffb4ab"));
            if (_statusLabel is not null)
            {
                _statusLabel.Text = "Pairing code expired";
                _statusLabel.AddThemeColorOverride("font_color", new Color("ffb4ab"));
            }
            return;
        }

        _expiryLabel.Text = $"One-time code expires in {remaining / 60:00}:{remaining % 60:00}";
    }

    private static PanelContainer StyledPanel(
        Color color,
        int radius,
        int horizontalPadding,
        int verticalPadding)
    {
        var panel = new PanelContainer();
        panel.AddThemeStyleboxOverride(
            "panel",
            new StyleBoxFlat
            {
                BgColor = color,
                CornerRadiusTopLeft = radius,
                CornerRadiusTopRight = radius,
                CornerRadiusBottomLeft = radius,
                CornerRadiusBottomRight = radius,
                ContentMarginLeft = horizontalPadding,
                ContentMarginRight = horizontalPadding,
                ContentMarginTop = verticalPadding,
                ContentMarginBottom = verticalPadding,
            });
        return panel;
    }

    private static Label StyledLabel(
        string value,
        int fontSize,
        Color color,
        FontWeight weight = FontWeight.Normal,
        HorizontalAlignment alignment = HorizontalAlignment.Left)
    {
        var label = new Label
        {
            Text = value,
            HorizontalAlignment = alignment,
        };
        label.AddThemeFontSizeOverride("font_size", fontSize);
        label.AddThemeColorOverride("font_color", color);
        if (weight != FontWeight.Normal)
        {
            label.AddThemeConstantOverride("outline_size", weight == FontWeight.Bold ? 2 : 1);
            label.AddThemeColorOverride("font_outline_color", color);
        }
        return label;
    }

    private static Label Paragraph(
        string value,
        int fontSize,
        Color color,
        float width,
        HorizontalAlignment alignment = HorizontalAlignment.Left)
    {
        Label label = StyledLabel(value, fontSize, color, FontWeight.Normal, alignment);
        label.AutowrapMode = TextServer.AutowrapMode.WordSmart;
        label.CustomMinimumSize = new Vector2(width, 0.0f);
        return label;
    }

    private enum FontWeight
    {
        Normal,
        SemiBold,
        Bold,
    }
}
