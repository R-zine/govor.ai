[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $InstallRoot
)

$ErrorActionPreference = 'Stop'
$resolvedRoot = [IO.Path]::GetFullPath($InstallRoot)
$python = Join-Path $resolvedRoot 'runtime\python\python.exe'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    [Windows.Forms.MessageBox]::Show(
        'The packaged Python runtime is missing. Extract the complete govor.ai archive first.',
        'govor.ai lesson creator',
        [Windows.Forms.MessageBoxButtons]::OK,
        [Windows.Forms.MessageBoxIcon]::Error
    ) | Out-Null
    exit 2
}

$form = New-Object Windows.Forms.Form
$form.Text = 'Create a lesson with govor.ai'
$form.StartPosition = [Windows.Forms.FormStartPosition]::CenterScreen
$form.ClientSize = New-Object Drawing.Size(540, 430)
$form.FormBorderStyle = [Windows.Forms.FormBorderStyle]::FixedDialog
$form.MaximizeBox = $false
$form.MinimizeBox = $false

$intro = New-Object Windows.Forms.Label
$intro.Location = New-Object Drawing.Point(18, 16)
$intro.Size = New-Object Drawing.Size(504, 42)
$intro.Text = 'Describe what the lesson should teach. Start-Govor.cmd must already be running so the local language model is available.'
$form.Controls.Add($intro)

$topicLabel = New-Object Windows.Forms.Label
$topicLabel.Location = New-Object Drawing.Point(18, 66)
$topicLabel.Size = New-Object Drawing.Size(504, 20)
$topicLabel.Text = 'Lesson topic or goal (required)'
$form.Controls.Add($topicLabel)

$topicBox = New-Object Windows.Forms.TextBox
$topicBox.Location = New-Object Drawing.Point(18, 88)
$topicBox.Size = New-Object Drawing.Size(504, 92)
$topicBox.Multiline = $true
$topicBox.MaxLength = 500
$topicBox.ScrollBars = [Windows.Forms.ScrollBars]::Vertical
$form.Controls.Add($topicBox)

$difficultyLabel = New-Object Windows.Forms.Label
$difficultyLabel.Location = New-Object Drawing.Point(18, 198)
$difficultyLabel.Size = New-Object Drawing.Size(150, 20)
$difficultyLabel.Text = 'Content difficulty'
$form.Controls.Add($difficultyLabel)

$difficultyBox = New-Object Windows.Forms.ComboBox
$difficultyBox.Location = New-Object Drawing.Point(18, 220)
$difficultyBox.Size = New-Object Drawing.Size(235, 24)
$difficultyBox.DropDownStyle = [Windows.Forms.ComboBoxStyle]::DropDownList
[void]$difficultyBox.Items.AddRange(@('Automatic (intermediate)', 'Beginner', 'Intermediate', 'Advanced'))
$difficultyBox.SelectedIndex = 0
$form.Controls.Add($difficultyBox)

$environmentLabel = New-Object Windows.Forms.Label
$environmentLabel.Location = New-Object Drawing.Point(287, 198)
$environmentLabel.Size = New-Object Drawing.Size(150, 20)
$environmentLabel.Text = 'Visual environment'
$form.Controls.Add($environmentLabel)

$environmentBox = New-Object Windows.Forms.ComboBox
$environmentBox.Location = New-Object Drawing.Point(287, 220)
$environmentBox.Size = New-Object Drawing.Size(235, 24)
$environmentBox.DropDownStyle = [Windows.Forms.ComboBoxStyle]::DropDownList
[void]$environmentBox.Items.AddRange(@('Automatic', 'Cafe', 'Supermarket', 'Airport', 'Home'))
$environmentBox.SelectedIndex = 0
$form.Controls.Add($environmentBox)

$lengthLabel = New-Object Windows.Forms.Label
$lengthLabel.Location = New-Object Drawing.Point(18, 268)
$lengthLabel.Size = New-Object Drawing.Size(180, 20)
$lengthLabel.Text = 'Lesson length (exercises)'
$form.Controls.Add($lengthLabel)

$lengthBox = New-Object Windows.Forms.NumericUpDown
$lengthBox.Location = New-Object Drawing.Point(18, 290)
$lengthBox.Size = New-Object Drawing.Size(90, 24)
$lengthBox.Minimum = 1
$lengthBox.Maximum = 8
$lengthBox.Value = 5
$lengthBox.Enabled = $false
$form.Controls.Add($lengthBox)

$automaticLength = New-Object Windows.Forms.CheckBox
$automaticLength.Location = New-Object Drawing.Point(122, 290)
$automaticLength.Size = New-Object Drawing.Size(210, 24)
$automaticLength.Text = 'Choose automatically (5)'
$automaticLength.Checked = $true
$automaticLength.Add_CheckedChanged({ $lengthBox.Enabled = -not $automaticLength.Checked })
$form.Controls.Add($automaticLength)

$privacy = New-Object Windows.Forms.Label
$privacy.Location = New-Object Drawing.Point(18, 330)
$privacy.Size = New-Object Drawing.Size(504, 36)
$privacy.Text = 'Generation stays on this PC. The result is validated before it is added to the lesson catalog.'
$form.Controls.Add($privacy)

$cancelButton = New-Object Windows.Forms.Button
$cancelButton.Location = New-Object Drawing.Point(332, 382)
$cancelButton.Size = New-Object Drawing.Size(90, 30)
$cancelButton.Text = 'Cancel'
$cancelButton.DialogResult = [Windows.Forms.DialogResult]::Cancel
$form.CancelButton = $cancelButton
$form.Controls.Add($cancelButton)

$createButton = New-Object Windows.Forms.Button
$createButton.Location = New-Object Drawing.Point(432, 382)
$createButton.Size = New-Object Drawing.Size(90, 30)
$createButton.Text = 'Create'
$createButton.DialogResult = [Windows.Forms.DialogResult]::OK
$form.AcceptButton = $createButton
$form.Controls.Add($createButton)

$topicBox.Select()
if ($form.ShowDialog() -ne [Windows.Forms.DialogResult]::OK) {
    exit 0
}
$topic = $topicBox.Text.Trim()
if (-not $topic) {
    [Windows.Forms.MessageBox]::Show(
        'Enter a lesson topic or goal.',
        'Lesson topic required',
        [Windows.Forms.MessageBoxButtons]::OK,
        [Windows.Forms.MessageBoxIcon]::Warning
    ) | Out-Null
    exit 2
}

$sourceRoots = @(
    'apps\launcher\src',
    'packages\domain\src',
    'packages\gateway_security\src',
    'packages\provider_interfaces\src',
    'packages\scene_planner\src',
    'packages\contracts\python',
    'services\local_ai\src'
) | ForEach-Object { Join-Path (Join-Path $resolvedRoot 'app') $_ }
$arguments = @(
    '-m', 'govor_launcher.cli', '--install-root', $resolvedRoot,
    'create-lesson', '--topic', $topic
)
$difficultyValues = @('', 'beginner', 'intermediate', 'advanced')
if ($difficultyBox.SelectedIndex -gt 0) {
    $arguments += @('--difficulty', $difficultyValues[$difficultyBox.SelectedIndex])
}
$environmentValues = @('', 'cafe', 'supermarket', 'airport', 'home')
if ($environmentBox.SelectedIndex -gt 0) {
    $arguments += @('--environment', $environmentValues[$environmentBox.SelectedIndex])
}
if (-not $automaticLength.Checked) {
    $arguments += @('--exercise-count', [string][int]$lengthBox.Value)
}

$previousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = $sourceRoots -join [IO.Path]::PathSeparator
$previousErrorActionPreference = $ErrorActionPreference
try {
    $ErrorActionPreference = 'Continue'
    $output = & $python @arguments 2>&1
    $exitCode = $LASTEXITCODE
}
finally {
    $ErrorActionPreference = $previousErrorActionPreference
    $env:PYTHONPATH = $previousPythonPath
}

$message = ($output | Out-String).Trim()
if ($exitCode -eq 0) {
    [Windows.Forms.MessageBox]::Show(
        "$message`n`nThe Android lesson list will update without restarting govor.ai.",
        'Lesson created',
        [Windows.Forms.MessageBoxButtons]::OK,
        [Windows.Forms.MessageBoxIcon]::Information
    ) | Out-Null
    exit 0
}
if (-not $message) {
    $message = 'The lesson could not be generated. Make sure Start-Govor.cmd is running.'
}
[Windows.Forms.MessageBox]::Show(
    $message,
    'Lesson creation failed',
    [Windows.Forms.MessageBoxButtons]::OK,
    [Windows.Forms.MessageBoxIcon]::Error
) | Out-Null
exit $exitCode
