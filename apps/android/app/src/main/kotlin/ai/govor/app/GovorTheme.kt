package ai.govor.app

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

private val GovorColors = darkColorScheme(
    primary = Color(0xFF73DBC3),
    onPrimary = Color(0xFF00382E),
    primaryContainer = Color(0xFF005143),
    onPrimaryContainer = Color(0xFF94F8DE),
    secondary = Color(0xFFB1CCC4),
    onSecondary = Color(0xFF1C352F),
    secondaryContainer = Color(0xFF334B45),
    onSecondaryContainer = Color(0xFFCDE8E0),
    tertiary = Color(0xFFACCBE4),
    onTertiary = Color(0xFF143349),
    surface = Color(0xFF0E1513),
    surfaceVariant = Color(0xFF3F4945),
    onSurface = Color(0xFFDEE4E0),
    onSurfaceVariant = Color(0xFFBFC9C4),
    error = Color(0xFFFFB4AB),
    onError = Color(0xFF690005),
)

private val GovorTypography = Typography(
    headlineSmall = TextStyle(
        fontSize = 26.sp,
        lineHeight = 32.sp,
        fontWeight = FontWeight.SemiBold,
    ),
    titleLarge = TextStyle(
        fontSize = 22.sp,
        lineHeight = 28.sp,
        fontWeight = FontWeight.SemiBold,
    ),
    bodyLarge = TextStyle(
        fontSize = 18.sp,
        lineHeight = 26.sp,
    ),
    labelLarge = TextStyle(
        fontSize = 16.sp,
        lineHeight = 22.sp,
        fontWeight = FontWeight.SemiBold,
    ),
)

@Composable
internal fun GovorTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = GovorColors,
        typography = GovorTypography,
        content = content,
    )
}
