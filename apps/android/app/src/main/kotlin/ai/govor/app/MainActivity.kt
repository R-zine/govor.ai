package ai.govor.app

import android.Manifest
import android.content.pm.PackageManager
import android.net.ConnectivityManager
import android.net.Network
import android.os.Bundle
import ai.govor.core.SessionState
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.waitForUpOrCancellation
import androidx.compose.foundation.text.ClickableText
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
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

@Composable
private fun GovorApp(model: MediaSessionViewModel = viewModel()) {
    val status by model.session.status.collectAsStateWithLifecycle()
    val mediaError by model.session.error.collectAsStateWithLifecycle()
    val lessonState by model.lesson.state.collectAsStateWithLifecycle()
    val lessonError by model.lesson.error.collectAsStateWithLifecycle()
    val pairingError by model.pairingError.collectAsStateWithLifecycle()
    val teacherText by model.lesson.teacherText.collectAsStateWithLifecycle()
    val pronunciations by model.lesson.pronunciations.collectAsStateWithLifecycle()
    val highlightedWordIndex by model.lesson.highlightedWordIndex.collectAsStateWithLifecycle()
    val selectedPronunciation by model.lesson.selectedPronunciation.collectAsStateWithLifecycle()
    val playbackRate by model.lesson.playbackRate.collectAsStateWithLifecycle()
    val transcript by model.lesson.transcript.collectAsStateWithLifecycle()
    val lessonProgress by model.lesson.lessonProgress.collectAsStateWithLifecycle()
    // Debug emulator defaults use adb reverse for control 8765 and media 8766.
    var mediaHost by rememberSaveable {
        mutableStateOf(if (BuildConfig.DEBUG) "127.0.0.1:8766" else "")
    }
    var controlHost by rememberSaveable {
        mutableStateOf(if (BuildConfig.DEBUG) "127.0.0.1:8765" else "")
    }
    var token by rememberSaveable { mutableStateOf("") }
    var certificateFingerprint by rememberSaveable { mutableStateOf("") }
    var scenarioId by rememberSaveable { mutableStateOf("cafe-ordering") }
    var englishLocale by rememberSaveable { mutableStateOf("en-GB") }
    var spacedReviewEnabled by rememberSaveable { mutableStateOf(false) }
    val context = LocalContext.current
    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted ->
        if (granted) {
            model.connect(
                mediaHost,
                controlHost,
                token,
                certificateFingerprint,
                scenarioId,
                englishLocale,
                spacedReviewEnabled,
            )
        }
    }

    MaterialTheme {
        Surface(color = Color(0xFF10201D), modifier = Modifier.fillMaxSize()) {
            Box(modifier = Modifier.fillMaxSize()) {
                AndroidView(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(Color(0xFF263D38)),
                    factory = { androidContext ->
                        SurfaceViewRenderer(androidContext).apply {
                            init(model.session.eglContext, null)
                            setScalingType(RendererCommon.ScalingType.SCALE_ASPECT_FIT)
                            setEnableHardwareScaler(true)
                            model.session.attachRenderer(this)
                        }
                    },
                    onRelease = { view ->
                        model.session.detachRenderer(view)
                        view.release()
                    },
                )

                Text(
                    "media: ${status.name.lowercase().replace('_', ' ')} · " +
                        "lesson: ${lessonState.name.lowercase().replace('_', ' ')}",
                    color = statusColor(status),
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier
                        .align(Alignment.TopStart)
                        .padding(24.dp),
                )

                if (
                    status == MediaConnectionStatus.DISCONNECTED ||
                    status == MediaConnectionStatus.FAILED
                ) {
                    Column(
                        modifier = Modifier
                            .align(Alignment.Center)
                            .fillMaxWidth()
                            .padding(24.dp)
                            .background(Color(0xE610201D), MaterialTheme.shapes.large)
                            .padding(20.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                    ) {
                        Text("govor.ai session", color = Color.White, fontSize = 22.sp)
                        OutlinedTextField(
                            value = mediaHost,
                            onValueChange = { mediaHost = it },
                            singleLine = true,
                            label = { Text("Media host:port") },
                            modifier = Modifier.fillMaxWidth(),
                        )
                        OutlinedTextField(
                            value = controlHost,
                            onValueChange = { controlHost = it },
                            singleLine = true,
                            label = { Text("Control host:port") },
                            modifier = Modifier.fillMaxWidth(),
                        )
                        OutlinedTextField(
                            value = token,
                            onValueChange = { token = it },
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
                                onValueChange = { certificateFingerprint = it },
                                singleLine = true,
                                label = { Text("PC certificate SHA-256") },
                                modifier = Modifier.fillMaxWidth(),
                            )
                        }
                        Text("Guided scenario", color = Color.White)
                        GUIDED_SCENARIOS.chunked(2).forEach { scenarioRow ->
                            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                scenarioRow.forEach { scenario ->
                                    Button(onClick = { scenarioId = scenario.first }) {
                                        Text(
                                            if (scenarioId == scenario.first) {
                                                "${scenario.second} ✓"
                                            } else {
                                                scenario.second
                                            },
                                        )
                                    }
                                }
                            }
                        }
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            listOf("en-GB", "en-US").forEach { locale ->
                                Button(onClick = { englishLocale = locale }) {
                                    Text(if (englishLocale == locale) "$locale ✓" else locale)
                                }
                            }
                        }
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Checkbox(
                                checked = spacedReviewEnabled,
                                onCheckedChange = { spacedReviewEnabled = it },
                            )
                            Text("Enable spaced vocabulary review", color = Color.White)
                        }
                        Button(
                            onClick = {
                                val microphonePermission = ContextCompat.checkSelfPermission(
                                    context,
                                    Manifest.permission.RECORD_AUDIO,
                                )
                                if (microphonePermission == PackageManager.PERMISSION_GRANTED) {
                                    model.connect(
                                        mediaHost,
                                        controlHost,
                                        token,
                                        certificateFingerprint,
                                        scenarioId,
                                        englishLocale,
                                        spacedReviewEnabled,
                                    )
                                } else {
                                    permissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
                                }
                            },
                            modifier = Modifier.fillMaxWidth(),
                        ) {
                            Text("Connect")
                        }
                        mediaError?.let { Text(it, color = Color(0xFFFFB4AB)) }
                        lessonError?.let { Text(it, color = Color(0xFFFFB4AB)) }
                        pairingError?.let { Text(it, color = Color(0xFFFFB4AB)) }
                    }
                }

                if (status == MediaConnectionStatus.CONNECTED) {
                    Column(
                        modifier = Modifier
                            .align(Alignment.BottomCenter)
                            .padding(bottom = 40.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(16.dp),
                    ) {
                        lessonProgress?.let { progress ->
                            Text(
                                "${progress.scenario_title} · " +
                                    "${progress.exercise_number}/${progress.exercise_count} · " +
                                    progress.difficulty,
                                color = Color(0xFFB8D9D1),
                                fontWeight = FontWeight.SemiBold,
                            )
                            progress.difficulty_change_reason?.let { reason ->
                                Text(
                                    when (reason) {
                                        "repeated_difficulty" ->
                                            "Difficulty reduced after repeated difficulty."
                                        else ->
                                            "Difficulty increased after consistent first-try success."
                                    },
                                    color = Color(0xFFB8D9D1),
                                )
                            }
                            if (progress.status == "completed") {
                                Text("Lesson complete · progress saved", color = Color(0xFF83F8DA))
                            }
                        }
                        teacherText?.let { text ->
                            val annotated = buildAnnotatedString {
                                append("Teacher: ")
                                val prefixLength = length
                                append(text)
                                pronunciations.forEachIndexed { index, pronunciation ->
                                    val start = prefixLength + pronunciation.start_char
                                    val end = prefixLength + pronunciation.end_char
                                    addStringAnnotation("word", index.toString(), start, end)
                                    addStyle(
                                        SpanStyle(
                                            color = Color.White,
                                            background = if (index == highlightedWordIndex) {
                                                Color(0xFF00796B)
                                            } else {
                                                Color.Transparent
                                            },
                                            textDecoration = TextDecoration.Underline,
                                        ),
                                        start,
                                        end,
                                    )
                                }
                            }
                            ClickableText(
                                text = annotated,
                                style = MaterialTheme.typography.bodyLarge.copy(
                                    color = Color.White,
                                    fontSize = 18.sp,
                                ),
                                onClick = { offset ->
                                    annotated.getStringAnnotations("word", offset, offset)
                                        .firstOrNull()
                                        ?.item
                                        ?.toIntOrNull()
                                        ?.let(model.lesson::selectWord)
                                },
                            )
                        }
                        if (teacherText != null) {
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                Button(
                                    onClick = model.lesson::replayTurn,
                                    enabled = lessonState == SessionState.AWAITING_LEARNER,
                                ) { Text("Replay") }
                                ai.govor.core.SpeechTimeline.supportedRates.forEach { rate ->
                                    Button(onClick = { model.lesson.setPlaybackRate(rate) }) {
                                        Text(
                                            if (rate == playbackRate) "${rate}× ✓" else "${rate}×",
                                        )
                                    }
                                }
                            }
                        }
                        if (pronunciations.isNotEmpty()) {
                            LazyRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                itemsIndexed(pronunciations) { index, pronunciation ->
                                    Button(onClick = { model.lesson.selectWord(index) }) {
                                        Text(pronunciation.word)
                                    }
                                }
                            }
                        }
                        selectedPronunciation?.let { pronunciation ->
                            Column(
                                modifier = Modifier
                                    .fillMaxWidth(0.9f)
                                    .background(Color(0xE6263D38), MaterialTheme.shapes.medium)
                                    .padding(12.dp),
                                horizontalAlignment = Alignment.CenterHorizontally,
                            ) {
                                Text(
                                    "${pronunciation.word}  /${pronunciation.ipa}/",
                                    color = Color.White,
                                    fontWeight = FontWeight.Bold,
                                )
                                pronunciation.explanation?.let { explanation ->
                                    Text(explanation, color = Color(0xFFB8D9D1))
                                }
                            }
                        }
                        transcript?.let {
                            Text("You: $it", color = Color(0xFFB8D9D1), fontSize = 15.sp)
                        }
                        Text(
                            if (lessonState == SessionState.AWAITING_LEARNER) {
                                "Hold while speaking"
                            } else {
                                lessonState.name.lowercase().replace('_', ' ')
                            },
                            color = Color.White,
                            fontSize = 20.sp,
                        )
                        Row(horizontalArrangement = Arrangement.spacedBy(24.dp)) {
                            Button(onClick = model::disconnect) { Text("Disconnect") }
                            if (
                                lessonState == SessionState.AWAITING_LEARNER ||
                                lessonState == SessionState.RECORDING
                            ) {
                                Box(
                                    contentAlignment = Alignment.Center,
                                    modifier = Modifier
                                        .size(96.dp)
                                        .background(Color(0xFF00A88F), CircleShape)
                                        .pointerInput(Unit) {
                                            awaitEachGesture {
                                                awaitFirstDown(requireUnconsumed = false)
                                                model.setPushToTalk(true)
                                                waitForUpOrCancellation()
                                                model.setPushToTalk(false)
                                            }
                                        },
                                ) {
                                    Text(
                                        "Hold\nto talk",
                                        color = Color.White,
                                        fontSize = 16.sp,
                                        fontWeight = FontWeight.Bold,
                                    )
                                }
                            } else if (lessonState == SessionState.RECOVERABLE_ERROR) {
                                Button(onClick = model.lesson::retry) { Text("Retry lesson") }
                            }
                        }
                    }
                }
            }
        }
    }
}

private val GUIDED_SCENARIOS = listOf(
    "cafe-ordering" to "Café",
    "supermarket-shopping" to "Supermarket",
    "airport-travel" to "Airport",
    "home-conversation" to "Home",
)

private fun statusColor(status: MediaConnectionStatus): Color = when (status) {
    MediaConnectionStatus.CONNECTED -> Color(0xFF83F8DA)
    MediaConnectionStatus.FAILED -> Color(0xFFFFB4AB)
    else -> Color.White
}
