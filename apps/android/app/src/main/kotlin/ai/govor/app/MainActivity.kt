package ai.govor.app

import android.Manifest
import android.content.pm.PackageManager
import android.net.ConnectivityManager
import android.net.Network
import android.os.Bundle
import ai.govor.core.LessonCatalogItemPayload
import ai.govor.core.LessonCatalogProgressPayload
import ai.govor.core.LessonProgressPayload
import ai.govor.core.PairingBootstrapCodec
import ai.govor.core.PronunciationPayload
import ai.govor.core.SessionState
import ai.govor.core.SpeechTimeline
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.waitForUpOrCancellation
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.automirrored.filled.VolumeUp
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.ExpandLess
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Replay
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Speed
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material.icons.filled.Wifi
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledIconButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.ListItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.LinkAnnotation
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.journeyapps.barcodescanner.ScanContract
import com.journeyapps.barcodescanner.ScanOptions
import org.webrtc.RendererCommon
import org.webrtc.SurfaceViewRenderer

class MainActivity : ComponentActivity() {
    private val model: MediaSessionViewModel by viewModels()
    private val connectivityManager by lazy {
        getSystemService(ConnectivityManager::class.java)
    }
    private val networkCallback = object : ConnectivityManager.NetworkCallback() {
        override fun onAvailable(network: Network) {
            model.networkAvailable()
        }
    }
    private var networkCallbackRegistered = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent { GovorApp(model) }
    }

    override fun onStart() {
        super.onStart()
        model.enterForeground()
        connectivityManager.registerDefaultNetworkCallback(networkCallback)
        networkCallbackRegistered = true
    }

    override fun onStop() {
        if (networkCallbackRegistered) {
            connectivityManager.unregisterNetworkCallback(networkCallback)
            networkCallbackRegistered = false
        }
        model.enterBackground()
        super.onStop()
    }
}

private data class ConnectionDetails(
    val mediaHost: String,
    val controlHost: String,
    val pairingCode: String,
    val certificateFingerprint: String,
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun GovorApp(model: MediaSessionViewModel = viewModel()) {
    val mediaStatus by model.session.status.collectAsStateWithLifecycle()
    val mediaError by model.session.error.collectAsStateWithLifecycle()
    val lessonState by model.lesson.state.collectAsStateWithLifecycle()
    val lessonError by model.lesson.error.collectAsStateWithLifecycle()
    val pairingError by model.pairingError.collectAsStateWithLifecycle()
    val savedGatewayHosts by model.savedGatewayHosts.collectAsStateWithLifecycle()
    val teacherText by model.lesson.teacherText.collectAsStateWithLifecycle()
    val pronunciations by model.lesson.pronunciations.collectAsStateWithLifecycle()
    val highlightedWordIndex by model.lesson.highlightedWordIndex.collectAsStateWithLifecycle()
    val selectedPronunciation by model.lesson.selectedPronunciation.collectAsStateWithLifecycle()
    val playbackRate by model.lesson.playbackRate.collectAsStateWithLifecycle()
    val transcript by model.lesson.transcript.collectAsStateWithLifecycle()
    val lessonProgress by model.lesson.lessonProgress.collectAsStateWithLifecycle()
    val lessonCatalog by model.lesson.lessonCatalog.collectAsStateWithLifecycle()
    val lessonActive by model.lesson.lessonActive.collectAsStateWithLifecycle()

    var mediaHost by rememberSaveable {
        mutableStateOf(
            if (BuildConfig.DEBUG) "127.0.0.1:8766"
            else savedGatewayHosts?.mediaHost.orEmpty(),
        )
    }
    var controlHost by rememberSaveable {
        mutableStateOf(
            if (BuildConfig.DEBUG) "127.0.0.1:8765"
            else savedGatewayHosts?.controlHost.orEmpty(),
        )
    }
    var token by rememberSaveable { mutableStateOf("") }
    var certificateFingerprint by rememberSaveable { mutableStateOf("") }
    var scenarioId by rememberSaveable { mutableStateOf("") }
    var englishLocale by rememberSaveable { mutableStateOf("en-GB") }
    var spacedReviewEnabled by rememberSaveable { mutableStateOf(false) }
    var qrError by rememberSaveable { mutableStateOf<String?>(null) }
    var pendingConnection by remember { mutableStateOf<ConnectionDetails?>(null) }

    LaunchedEffect(lessonCatalog) {
        if (lessonCatalog.none { it.scenario_id == scenarioId }) {
            scenarioId = lessonCatalog.firstOrNull()?.scenario_id.orEmpty()
        }
    }

    val context = LocalContext.current
    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted ->
        val connection = pendingConnection
        pendingConnection = null
        if (granted && connection != null) {
            model.connect(
                connection.mediaHost,
                connection.controlHost,
                connection.pairingCode,
                connection.certificateFingerprint,
            )
        }
    }
    val requestConnection: (ConnectionDetails) -> Unit = { connection ->
        if (
            ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) ==
            PackageManager.PERMISSION_GRANTED
        ) {
            model.connect(
                connection.mediaHost,
                connection.controlHost,
                connection.pairingCode,
                connection.certificateFingerprint,
            )
        } else {
            pendingConnection = connection
            permissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
        }
    }
    val scanLauncher = rememberLauncherForActivityResult(ScanContract()) { result ->
        val contents = result.contents ?: return@rememberLauncherForActivityResult
        runCatching {
            PairingBootstrapCodec.decode(contents, System.currentTimeMillis() / 1_000L)
        }.onSuccess { pairing ->
            qrError = null
            mediaHost = pairing.media_host
            controlHost = pairing.control_host
            token = pairing.pairing_code
            certificateFingerprint = pairing.certificate_sha256
            requestConnection(
                ConnectionDetails(
                    pairing.media_host,
                    pairing.control_host,
                    pairing.pairing_code,
                    pairing.certificate_sha256,
                ),
            )
        }.onFailure { error ->
            qrError = "That pairing QR could not be used: ${error.message ?: "invalid data"}."
        }
    }
    val scanPairingQr = {
        scanLauncher.launch(
            ScanOptions()
                .setDesiredBarcodeFormats(ScanOptions.QR_CODE)
                .setPrompt("Point the camera at the QR shown on the govor.ai host")
                .setBeepEnabled(false)
                .setBarcodeImageEnabled(false)
                .setOrientationLocked(false),
        )
    }
    val manualConnection = {
        qrError = null
        requestConnection(
            ConnectionDetails(mediaHost, controlHost, token, certificateFingerprint),
        )
    }

    val screen = resolveGovorScreen(
        mediaConnected = mediaStatus == MediaConnectionStatus.CONNECTED,
        lessonActive = lessonActive,
    )

    GovorTheme {
        Surface(
            color = MaterialTheme.colorScheme.surface,
            modifier = Modifier.fillMaxSize(),
        ) {
            Box(modifier = Modifier.fillMaxSize()) {
                VideoSurface(model)
                when (screen) {
                    GovorScreen.CONNECTION -> ConnectionScreen(
                        mediaStatus = mediaStatus,
                        lessonState = lessonState,
                        mediaHost = mediaHost,
                        onMediaHostChanged = { mediaHost = it },
                        controlHost = controlHost,
                        onControlHostChanged = { controlHost = it },
                        token = token,
                        onTokenChanged = { token = it },
                        certificateFingerprint = certificateFingerprint,
                        onCertificateFingerprintChanged = { certificateFingerprint = it },
                        onConnect = manualConnection,
                        onScanQr = scanPairingQr,
                        hasSavedGateway = savedGatewayHosts != null,
                        onReconnectSaved = {
                            qrError = null
                            requestConnection(
                                ConnectionDetails(mediaHost, controlHost, "", ""),
                            )
                        },
                        errors = listOfNotNull(mediaError, lessonError, pairingError, qrError),
                    )

                    GovorScreen.LESSON_SELECTION -> LessonSelectionScreen(
                        lessonCatalog = lessonCatalog,
                        selectedScenarioId = scenarioId,
                        onScenarioSelected = { scenarioId = it },
                        englishLocale = englishLocale,
                        onEnglishLocaleChanged = { englishLocale = it },
                        spacedReviewEnabled = spacedReviewEnabled,
                        onSpacedReviewChanged = { spacedReviewEnabled = it },
                        lessonProgress = lessonProgress,
                        lessonState = lessonState,
                        onStartLesson = {
                            model.startLesson(
                                scenarioId,
                                englishLocale,
                                spacedReviewEnabled,
                            )
                        },
                        onDisconnect = model::disconnect,
                        errors = listOfNotNull(lessonError, pairingError),
                    )

                    GovorScreen.ACTIVE_LESSON -> ActiveLessonScreen(
                        mediaStatus = mediaStatus,
                        lessonState = lessonState,
                        teacherText = teacherText,
                        pronunciations = pronunciations,
                        highlightedWordIndex = highlightedWordIndex,
                        selectedPronunciation = selectedPronunciation,
                        playbackRate = playbackRate,
                        transcript = transcript,
                        lessonProgress = lessonProgress,
                        onReplay = model.lesson::replayTurn,
                        onPlaybackRateChanged = model.lesson::setPlaybackRate,
                        onWordSelected = model.lesson::selectWord,
                        onPushToTalkChanged = model::setPushToTalk,
                        onRetry = model.lesson::retry,
                        onDisconnect = model::disconnect,
                        errors = listOfNotNull(mediaError, lessonError, pairingError),
                    )
                }
            }
        }
    }
}

@Composable
private fun VideoSurface(model: MediaSessionViewModel) {
    AndroidView(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.surfaceVariant),
        factory = { androidContext ->
            SurfaceViewRenderer(androidContext).apply {
                init(model.session.eglContext, null)
                setScalingType(RendererCommon.ScalingType.SCALE_ASPECT_FILL)
                setEnableHardwareScaler(true)
                model.session.attachRenderer(this)
            }
        },
        onRelease = { view ->
            model.session.detachRenderer(view)
            view.release()
        },
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ConnectionScreen(
    mediaStatus: MediaConnectionStatus,
    lessonState: SessionState,
    mediaHost: String,
    onMediaHostChanged: (String) -> Unit,
    controlHost: String,
    onControlHostChanged: (String) -> Unit,
    token: String,
    onTokenChanged: (String) -> Unit,
    certificateFingerprint: String,
    onCertificateFingerprintChanged: (String) -> Unit,
    onConnect: () -> Unit,
    onScanQr: () -> Unit,
    hasSavedGateway: Boolean,
    onReconnectSaved: () -> Unit,
    errors: List<String>,
) {
    var showManualPairing by rememberSaveable { mutableStateOf(BuildConfig.DEBUG) }
    val connectionEnabled = mediaStatus !in setOf(
        MediaConnectionStatus.SIGNALING,
        MediaConnectionStatus.CONNECTING,
    ) && lessonState != SessionState.CONNECTING
    Scaffold(
        containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.96f),
        topBar = {
            CenterAlignedTopAppBar(
                title = { Text("govor.ai") },
                colors = opaqueTopAppBarColors(),
            )
        },
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
            contentPadding = PaddingValues(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            item {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Connect to your teacher", style = MaterialTheme.typography.headlineSmall)
                    Text(
                        if (BuildConfig.DEBUG) {
                            "Enter the development connection details."
                        } else {
                            "Scan the QR shown by the Windows host. The code is short-lived and " +
                                "your lessons load after the secure connection is ready."
                        },
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    ConnectionStatusPill(mediaStatus, lessonState)
                }
            }
            if (!BuildConfig.DEBUG) {
                item {
                    if (hasSavedGateway) {
                        Button(
                            onClick = onReconnectSaved,
                            enabled = connectionEnabled,
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(56.dp),
                        ) {
                            Icon(Icons.Filled.Wifi, contentDescription = null)
                            Spacer(Modifier.width(10.dp))
                            Text("Reconnect to saved host")
                        }
                        Spacer(Modifier.height(12.dp))
                        OutlinedButton(
                            onClick = onScanQr,
                            enabled = connectionEnabled,
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(56.dp),
                        ) {
                            Icon(Icons.Filled.QrCodeScanner, contentDescription = null)
                            Spacer(Modifier.width(10.dp))
                            Text("Scan a different host QR")
                        }
                    } else {
                        Button(
                            onClick = onScanQr,
                            enabled = connectionEnabled,
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(56.dp),
                        ) {
                            Icon(Icons.Filled.QrCodeScanner, contentDescription = null)
                            Spacer(Modifier.width(10.dp))
                            Text("Scan host QR")
                        }
                    }
                }
                item {
                    TextButton(
                        onClick = { showManualPairing = !showManualPairing },
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        Icon(
                            if (showManualPairing) Icons.Filled.ExpandLess
                            else Icons.Filled.ExpandMore,
                            contentDescription = null,
                        )
                        Spacer(Modifier.width(8.dp))
                        Text(if (showManualPairing) "Hide manual pairing" else "Pair manually")
                    }
                }
            }
            if (showManualPairing) item {
                Card(
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.7f),
                    ),
                ) {
                    Column(
                        modifier = Modifier.padding(20.dp),
                        verticalArrangement = Arrangement.spacedBy(14.dp),
                    ) {
                        OutlinedTextField(
                            value = mediaHost,
                            onValueChange = onMediaHostChanged,
                            singleLine = true,
                            label = { Text("Media host:port") },
                            modifier = Modifier.fillMaxWidth(),
                        )
                        OutlinedTextField(
                            value = controlHost,
                            onValueChange = onControlHostChanged,
                            singleLine = true,
                            label = { Text("Control host:port") },
                            modifier = Modifier.fillMaxWidth(),
                        )
                        OutlinedTextField(
                            value = token,
                            onValueChange = onTokenChanged,
                            singleLine = true,
                            label = {
                                Text(if (BuildConfig.DEBUG) "Development token" else "Pairing code")
                            },
                            visualTransformation = PasswordVisualTransformation(),
                            modifier = Modifier.fillMaxWidth(),
                        )
                        if (!BuildConfig.DEBUG) {
                            OutlinedTextField(
                                value = certificateFingerprint,
                                onValueChange = onCertificateFingerprintChanged,
                                singleLine = true,
                                label = { Text("PC certificate SHA-256") },
                                modifier = Modifier.fillMaxWidth(),
                            )
                        }
                        Button(
                            onClick = onConnect,
                            enabled = connectionEnabled,
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(56.dp),
                        ) {
                            Icon(Icons.Filled.Wifi, contentDescription = null)
                            Spacer(Modifier.width(10.dp))
                            Text(
                                if (BuildConfig.DEBUG) "Connect and load lessons"
                                else "Connect manually",
                            )
                        }
                    }
                }
            }
            if (errors.isNotEmpty()) {
                item { ErrorCard(errors) }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun LessonSelectionScreen(
    lessonCatalog: List<LessonCatalogItemPayload>,
    selectedScenarioId: String,
    onScenarioSelected: (String) -> Unit,
    englishLocale: String,
    onEnglishLocaleChanged: (String) -> Unit,
    spacedReviewEnabled: Boolean,
    onSpacedReviewChanged: (Boolean) -> Unit,
    lessonProgress: LessonProgressPayload?,
    lessonState: SessionState,
    onStartLesson: () -> Unit,
    onDisconnect: () -> Unit,
    errors: List<String>,
) {
    var showLessonPicker by rememberSaveable { mutableStateOf(false) }
    var showPreferences by rememberSaveable { mutableStateOf(false) }
    var showMore by rememberSaveable { mutableStateOf(false) }
    val selectedLesson = lessonCatalog.firstOrNull { it.scenario_id == selectedScenarioId }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.94f),
        topBar = {
            CenterAlignedTopAppBar(
                title = { Text("Choose a lesson") },
                actions = {
                    IconButton(onClick = { showLessonPicker = true }) {
                        Icon(Icons.AutoMirrored.Filled.List, contentDescription = "Choose lesson")
                    }
                    IconButton(onClick = { showPreferences = true }) {
                        Icon(Icons.Filled.Settings, contentDescription = "Lesson preferences")
                    }
                    Box {
                        IconButton(onClick = { showMore = true }) {
                            Icon(Icons.Filled.MoreVert, contentDescription = "More connection options")
                        }
                        DropdownMenu(
                            expanded = showMore,
                            onDismissRequest = { showMore = false },
                        ) {
                            DropdownMenuItem(
                                text = { Text("Disconnect") },
                                leadingIcon = { Icon(Icons.Filled.Close, contentDescription = null) },
                                onClick = {
                                    showMore = false
                                    onDisconnect()
                                },
                            )
                        }
                    }
                },
                colors = opaqueTopAppBarColors(),
            )
        },
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
            contentPadding = PaddingValues(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            item { ConnectionStatusPill(MediaConnectionStatus.CONNECTED, lessonState) }
            if (lessonProgress?.status == "completed") {
                item {
                    Card(
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.primaryContainer,
                        ),
                    ) {
                        Row(
                            modifier = Modifier.padding(16.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Icon(Icons.Filled.CheckCircle, contentDescription = null)
                            Spacer(Modifier.width(12.dp))
                            Text("Lesson complete · progress saved")
                        }
                    }
                }
            }
            if (lessonCatalog.isEmpty()) {
                item {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 64.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(16.dp),
                    ) {
                        CircularProgressIndicator()
                        Text("Loading lessons from the Windows host…")
                    }
                }
            } else {
                item {
                    Card(
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.8f),
                        ),
                    ) {
                        Column(
                            modifier = Modifier.padding(20.dp),
                            verticalArrangement = Arrangement.spacedBy(12.dp),
                        ) {
                            Text(
                                selectedLesson?.title ?: "Select a lesson",
                                style = MaterialTheme.typography.headlineSmall,
                            )
                            selectedLesson?.description?.let {
                                Text(it, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                            selectedLesson?.progress?.let { progress ->
                                LessonCatalogProgressStatus(progress)
                            }
                            TextButton(onClick = { showLessonPicker = true }) {
                                Icon(Icons.AutoMirrored.Filled.List, contentDescription = null)
                                Spacer(Modifier.width(8.dp))
                                Text("Browse ${lessonCatalog.size} lessons")
                            }
                        }
                    }
                }
                item {
                    Button(
                        onClick = onStartLesson,
                        enabled = selectedLesson != null,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(56.dp),
                    ) {
                        Icon(Icons.Filled.PlayArrow, contentDescription = null)
                        Spacer(Modifier.width(10.dp))
                        Text("Start lesson")
                    }
                }
            }
            if (errors.isNotEmpty()) {
                item { ErrorCard(errors) }
            }
        }
    }

    if (showLessonPicker) {
        ModalBottomSheet(onDismissRequest = { showLessonPicker = false }) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(max = 560.dp)
                    .verticalScroll(rememberScrollState())
                    .padding(bottom = 24.dp),
            ) {
                Text(
                    "Lessons",
                    style = MaterialTheme.typography.titleLarge,
                    modifier = Modifier.padding(horizontal = 24.dp, vertical = 12.dp),
                )
                lessonCatalog.forEach { lesson ->
                    ListItem(
                        headlineContent = { Text(lesson.title) },
                        supportingContent = {
                            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                Text(lesson.description)
                                Text(
                                    lessonCatalogProgressLabel(lesson.progress),
                                    color = if (lesson.progress.status == "completed") {
                                        MaterialTheme.colorScheme.primary
                                    } else {
                                        MaterialTheme.colorScheme.onSurfaceVariant
                                    },
                                    style = MaterialTheme.typography.labelMedium,
                                )
                            }
                        },
                        leadingContent = {
                            RadioButton(
                                selected = lesson.scenario_id == selectedScenarioId,
                                onClick = null,
                            )
                        },
                        modifier = Modifier.clickable {
                            onScenarioSelected(lesson.scenario_id)
                            showLessonPicker = false
                        },
                    )
                }
            }
        }
    }

    if (showPreferences) {
        LessonPreferencesSheet(
            englishLocale = englishLocale,
            onEnglishLocaleChanged = onEnglishLocaleChanged,
            spacedReviewEnabled = spacedReviewEnabled,
            onSpacedReviewChanged = onSpacedReviewChanged,
            onDismiss = { showPreferences = false },
        )
    }
}

@Composable
private fun LessonCatalogProgressStatus(progress: LessonCatalogProgressPayload) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Icon(
            if (progress.status == "completed") {
                Icons.Filled.CheckCircle
            } else {
                Icons.Filled.PlayArrow
            },
            contentDescription = null,
            tint = if (progress.status == "completed") {
                MaterialTheme.colorScheme.primary
            } else {
                MaterialTheme.colorScheme.onSurfaceVariant
            },
            modifier = Modifier.size(18.dp),
        )
        Text(
            lessonCatalogProgressLabel(progress),
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            style = MaterialTheme.typography.labelLarge,
        )
    }
}

internal fun lessonCatalogProgressLabel(progress: LessonCatalogProgressPayload): String =
    when (progress.status) {
        "completed" -> if (progress.completed_count == 1) {
            "Completed once"
        } else {
            "Completed ${progress.completed_count} times"
        }

        "in_progress" -> buildString {
            append("In progress · ${progress.successful_exercises}/${progress.exercise_count} complete")
            if (progress.completed_count > 0) {
                append(" · completed ${progress.completed_count} before")
            }
        }

        else -> "Not started"
    }

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun LessonPreferencesSheet(
    englishLocale: String,
    onEnglishLocaleChanged: (String) -> Unit,
    spacedReviewEnabled: Boolean,
    onSpacedReviewChanged: (Boolean) -> Unit,
    onDismiss: () -> Unit,
) {
    ModalBottomSheet(onDismissRequest = onDismiss) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 24.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text("Lesson preferences", style = MaterialTheme.typography.titleLarge)
            Text("Teacher accent", color = MaterialTheme.colorScheme.onSurfaceVariant)
            listOf(
                "en-GB" to "British English",
                "en-US" to "American English",
            ).forEach { (locale, label) ->
                ListItem(
                    headlineContent = { Text(label) },
                    supportingContent = { Text(locale) },
                    leadingContent = {
                        RadioButton(selected = englishLocale == locale, onClick = null)
                    },
                    modifier = Modifier.clickable { onEnglishLocaleChanged(locale) },
                )
            }
            HorizontalDivider()
            ListItem(
                headlineContent = { Text("Spaced vocabulary review") },
                supportingContent = { Text("Include words that are due for review") },
                trailingContent = {
                    Switch(
                        checked = spacedReviewEnabled,
                        onCheckedChange = onSpacedReviewChanged,
                    )
                },
                modifier = Modifier.clickable {
                    onSpacedReviewChanged(!spacedReviewEnabled)
                },
            )
            Spacer(Modifier.height(16.dp))
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ActiveLessonScreen(
    mediaStatus: MediaConnectionStatus,
    lessonState: SessionState,
    teacherText: String?,
    pronunciations: List<PronunciationPayload>,
    highlightedWordIndex: Int?,
    selectedPronunciation: PronunciationPayload?,
    playbackRate: Float,
    transcript: String?,
    lessonProgress: LessonProgressPayload?,
    onReplay: () -> Unit,
    onPlaybackRateChanged: (Float) -> Unit,
    onWordSelected: (Int) -> Unit,
    onPushToTalkChanged: (Boolean) -> Unit,
    onRetry: () -> Unit,
    onDisconnect: () -> Unit,
    errors: List<String>,
) {
    var showMore by rememberSaveable { mutableStateOf(false) }
    var showSpeedMenu by rememberSaveable { mutableStateOf(false) }
    var showPronunciations by rememberSaveable { mutableStateOf(false) }
    val controls = lessonControlVisibility(lessonState, teacherText != null)

    Scaffold(
        containerColor = Color.Transparent,
        topBar = {
            CenterAlignedTopAppBar(
                title = {
                    Text(
                        lessonProgress?.scenario_title ?: "Lesson",
                        maxLines = 1,
                    )
                },
                navigationIcon = {
                    ConnectionStatusDot(mediaStatus, lessonState)
                },
                actions = {
                    Box {
                        IconButton(onClick = { showMore = true }) {
                            Icon(Icons.Filled.MoreVert, contentDescription = "More lesson options")
                        }
                        DropdownMenu(
                            expanded = showMore,
                            onDismissRequest = { showMore = false },
                        ) {
                            DropdownMenuItem(
                                text = { Text("Disconnect") },
                                leadingIcon = { Icon(Icons.Filled.Close, contentDescription = null) },
                                onClick = {
                                    showMore = false
                                    onDisconnect()
                                },
                            )
                        }
                    }
                },
                colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.86f),
                    scrolledContainerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.94f),
                ),
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.Bottom,
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            lessonProgress?.let { ProgressCard(it) }
            Spacer(Modifier.height(10.dp))
            teacherText?.let { text ->
                SubtitleCard(
                    text = text,
                    pronunciations = pronunciations,
                    highlightedWordIndex = highlightedWordIndex,
                    selectedPronunciation = selectedPronunciation,
                    onWordSelected = onWordSelected,
                )
                Spacer(Modifier.height(10.dp))
            }
            transcript?.let {
                Surface(
                    shape = MaterialTheme.shapes.medium,
                    color = MaterialTheme.colorScheme.surface.copy(alpha = 0.86f),
                ) {
                    Text(
                        "You: $it",
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 10.dp),
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                Spacer(Modifier.height(10.dp))
            }
            if (controls.playbackActions) {
                Surface(
                    shape = CircleShape,
                    color = MaterialTheme.colorScheme.surface.copy(alpha = 0.88f),
                ) {
                    Row(
                        modifier = Modifier.padding(4.dp),
                        horizontalArrangement = Arrangement.spacedBy(4.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        IconButton(
                            onClick = onReplay,
                            enabled = lessonState == SessionState.AWAITING_LEARNER,
                        ) {
                            Icon(Icons.Filled.Replay, contentDescription = "Replay teacher")
                        }
                        Box {
                            IconButton(onClick = { showSpeedMenu = true }) {
                                Icon(
                                    Icons.Filled.Speed,
                                    contentDescription = "Playback speed ${formatRate(playbackRate)}",
                                )
                            }
                            DropdownMenu(
                                expanded = showSpeedMenu,
                                onDismissRequest = { showSpeedMenu = false },
                            ) {
                                SpeechTimeline.supportedRates.forEach { rate ->
                                    DropdownMenuItem(
                                        text = { Text(formatRate(rate)) },
                                        trailingIcon = {
                                            if (rate == playbackRate) {
                                                Icon(
                                                    Icons.Filled.CheckCircle,
                                                    contentDescription = "Selected",
                                                )
                                            }
                                        },
                                        onClick = {
                                            onPlaybackRateChanged(rate)
                                            showSpeedMenu = false
                                        },
                                    )
                                }
                            }
                        }
                        if (pronunciations.isNotEmpty()) {
                            IconButton(onClick = { showPronunciations = true }) {
                                Icon(
                                    Icons.AutoMirrored.Filled.VolumeUp,
                                    contentDescription = "Pronunciation words",
                                )
                            }
                        }
                    }
                }
                Spacer(Modifier.height(12.dp))
            }
            if (errors.isNotEmpty()) {
                ErrorCard(errors)
                Spacer(Modifier.height(12.dp))
            }
            when {
                controls.retry -> {
                    Button(onClick = onRetry) {
                        Icon(Icons.Filled.Refresh, contentDescription = null)
                        Spacer(Modifier.width(8.dp))
                        Text("Retry lesson")
                    }
                }

                controls.pushToTalk -> PushToTalkControl(
                    recording = lessonState == SessionState.RECORDING,
                    onPushToTalkChanged = onPushToTalkChanged,
                )

                else -> {
                    if (lessonState in setOf(SessionState.PROCESSING, SessionState.TEACHER_SPEAKING)) {
                        LinearProgressIndicator(modifier = Modifier.fillMaxWidth(0.72f))
                    }
                    Text(
                        lessonStateLabel(lessonState),
                        modifier = Modifier.padding(top = 10.dp),
                        color = MaterialTheme.colorScheme.onSurface,
                        style = MaterialTheme.typography.labelLarge,
                    )
                }
            }
        }
    }

    if (showPronunciations) {
        ModalBottomSheet(onDismissRequest = { showPronunciations = false }) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(max = 560.dp)
                    .verticalScroll(rememberScrollState())
                    .padding(bottom = 24.dp),
            ) {
                Text(
                    "Pronunciation",
                    style = MaterialTheme.typography.titleLarge,
                    modifier = Modifier.padding(horizontal = 24.dp, vertical = 12.dp),
                )
                pronunciations.forEachIndexed { index, pronunciation ->
                    ListItem(
                        headlineContent = { Text(pronunciation.word) },
                        supportingContent = {
                            Column {
                                Text("/${pronunciation.ipa}/")
                                pronunciation.explanation?.let { Text(it) }
                            }
                        },
                        leadingContent = {
                            Icon(Icons.AutoMirrored.Filled.VolumeUp, contentDescription = null)
                        },
                        modifier = Modifier.clickable {
                            onWordSelected(index)
                            showPronunciations = false
                        },
                    )
                }
            }
        }
    }
}

@Composable
private fun ProgressCard(progress: LessonProgressPayload) {
    Surface(
        shape = MaterialTheme.shapes.large,
        color = MaterialTheme.colorScheme.surface.copy(alpha = 0.86f),
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 10.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text(
                "${progress.exercise_number}/${progress.exercise_count} · ${progress.difficulty}",
                style = MaterialTheme.typography.labelLarge,
            )
            progress.difficulty_change_reason?.let { reason ->
                Text(
                    when (reason) {
                        "repeated_difficulty" -> "Difficulty reduced after repeated difficulty."
                        else -> "Difficulty increased after consistent first-try success."
                    },
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center,
                )
            }
        }
    }
}

@Composable
private fun SubtitleCard(
    text: String,
    pronunciations: List<PronunciationPayload>,
    highlightedWordIndex: Int?,
    selectedPronunciation: PronunciationPayload?,
    onWordSelected: (Int) -> Unit,
) {
    val annotated = buildAnnotatedString {
        append(text)
        pronunciations.forEachIndexed { index, pronunciation ->
            addStringAnnotation(
                tag = "word",
                annotation = index.toString(),
                start = pronunciation.start_char,
                end = pronunciation.end_char,
            )
            addLink(
                clickable = LinkAnnotation.Clickable(tag = index.toString()) {
                    onWordSelected(index)
                },
                start = pronunciation.start_char,
                end = pronunciation.end_char,
            )
            addStyle(
                SpanStyle(
                    color = MaterialTheme.colorScheme.onSurface,
                    background = if (index == highlightedWordIndex) {
                        MaterialTheme.colorScheme.primaryContainer
                    } else {
                        Color.Transparent
                    },
                    textDecoration = TextDecoration.Underline,
                ),
                start = pronunciation.start_char,
                end = pronunciation.end_char,
            )
        }
    }
    Card(
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.9f),
        ),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(
                "Teacher",
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.primary,
            )
            Text(
                text = annotated,
                style = MaterialTheme.typography.bodyLarge.copy(
                    color = MaterialTheme.colorScheme.onSurface,
                ),
                modifier = Modifier.semantics {
                    contentDescription = "Teacher: $text"
                },
            )
            selectedPronunciation?.let { pronunciation ->
                HorizontalDivider()
                Text(
                    "${pronunciation.word}  /${pronunciation.ipa}/",
                    fontWeight = FontWeight.Bold,
                )
                pronunciation.explanation?.let {
                    Text(it, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
    }
}

@Composable
private fun PushToTalkControl(
    recording: Boolean,
    onPushToTalkChanged: (Boolean) -> Unit,
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        FilledIconButton(
            onClick = {},
            modifier = Modifier
                .size(96.dp)
                .pointerInput(Unit) {
                    awaitEachGesture {
                        awaitFirstDown(requireUnconsumed = false)
                        onPushToTalkChanged(true)
                        waitForUpOrCancellation()
                        onPushToTalkChanged(false)
                    }
                }
                .semantics {
                    contentDescription = if (recording) "Release to send" else "Hold to talk"
                    role = Role.Button
                },
        ) {
            Icon(
                if (recording) Icons.Filled.Stop else Icons.Filled.Mic,
                contentDescription = null,
                modifier = Modifier.size(42.dp),
            )
        }
        Text(
            if (recording) "Release to send" else "Hold while speaking",
            style = MaterialTheme.typography.labelLarge,
        )
    }
}

@Composable
private fun ConnectionStatusPill(
    mediaStatus: MediaConnectionStatus,
    lessonState: SessionState,
) {
    val description = "media: ${mediaStatusLabel(mediaStatus)} · lesson: " +
        lessonState.name.lowercase().replace('_', ' ')
    Surface(
        shape = CircleShape,
        color = statusColor(mediaStatus).copy(alpha = 0.18f),
        modifier = Modifier.semantics(mergeDescendants = true) {
            contentDescription = description
        },
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(
                when (mediaStatus) {
                    MediaConnectionStatus.CONNECTED -> Icons.Filled.CheckCircle
                    MediaConnectionStatus.FAILED -> Icons.Filled.ErrorOutline
                    else -> Icons.Filled.Wifi
                },
                contentDescription = null,
                tint = statusColor(mediaStatus),
                modifier = Modifier.size(18.dp),
            )
            Spacer(Modifier.width(8.dp))
            Text(
                description,
                color = statusColor(mediaStatus),
                style = MaterialTheme.typography.labelLarge,
            )
        }
    }
}

@Composable
private fun ConnectionStatusDot(
    mediaStatus: MediaConnectionStatus,
    lessonState: SessionState,
) {
    val description = "media: ${mediaStatusLabel(mediaStatus)} · lesson: " +
        lessonState.name.lowercase().replace('_', ' ')
    Surface(
        shape = CircleShape,
        color = statusColor(mediaStatus),
        modifier = Modifier
            .padding(start = 16.dp)
            .size(14.dp)
            .semantics { contentDescription = description },
    ) {}
}

@Composable
private fun ErrorCard(errors: List<String>) {
    Card(
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.errorContainer,
            contentColor = MaterialTheme.colorScheme.onErrorContainer,
        ),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Filled.ErrorOutline, contentDescription = null)
                Spacer(Modifier.width(8.dp))
                Text("Needs attention", fontWeight = FontWeight.SemiBold)
            }
            errors.distinct().forEach { Text(it) }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun opaqueTopAppBarColors() = TopAppBarDefaults.centerAlignedTopAppBarColors(
    containerColor = MaterialTheme.colorScheme.surface,
    scrolledContainerColor = MaterialTheme.colorScheme.surface,
)

private fun formatRate(rate: Float): String = if (rate == 1.0f) "1×" else "${rate}×"

private fun mediaStatusLabel(status: MediaConnectionStatus): String =
    status.name.lowercase().replace('_', ' ')

private fun lessonStateLabel(state: SessionState): String = when (state) {
    SessionState.AWAITING_LEARNER -> "Your turn"
    SessionState.TEACHER_SPEAKING -> "Teacher is speaking"
    SessionState.PROCESSING -> "Preparing the next response"
    SessionState.CONNECTING -> "Starting lesson"
    else -> state.name.lowercase().replace('_', ' ')
}

@Composable
private fun statusColor(status: MediaConnectionStatus): Color = when (status) {
    MediaConnectionStatus.CONNECTED -> MaterialTheme.colorScheme.primary
    MediaConnectionStatus.FAILED -> MaterialTheme.colorScheme.error
    else -> MaterialTheme.colorScheme.onSurfaceVariant
}
