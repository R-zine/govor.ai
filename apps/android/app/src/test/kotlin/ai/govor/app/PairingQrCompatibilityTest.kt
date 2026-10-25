package ai.govor.app

import ai.govor.core.PairingBootstrapCodec
import com.google.zxing.BinaryBitmap
import com.google.zxing.RGBLuminanceSource
import com.google.zxing.qrcode.QRCodeReader
import com.google.zxing.common.HybridBinarizer
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test

class PairingQrCompatibilityTest {
    @Test
    fun `android decoder reads launcher generated segno QR`() {
        val modules = requireNotNull(javaClass.getResource("/pairing-bootstrap.modules.txt"))
            .readText()
            .trim()
            .lines()
        val scale = 4
        val border = 4
        val width = (modules.size + border * 2) * scale
        val pixels = IntArray(width * width) { -1 }
        modules.forEachIndexed { row, values ->
            require(values.length == modules.size)
            values.forEachIndexed { column, value ->
                if (value == '1') {
                    repeat(scale) { offsetY ->
                        repeat(scale) { offsetX ->
                            val x = (column + border) * scale + offsetX
                            val y = (row + border) * scale + offsetY
                            pixels[y * width + x] = 0xFF111827.toInt()
                        }
                    }
                }
            }
        }
        val decoded = QRCodeReader().decode(
            BinaryBitmap(
                HybridBinarizer(RGBLuminanceSource(width, width, pixels)),
            ),
        )

        val pairing = PairingBootstrapCodec.decode(decoded.text, 1_792_931_082L)

        assertEquals("192.168.100.78:8765", pairing.control_host)
        assertEquals("192.168.100.78:8766", pairing.media_host)
        assertEquals("12345678", pairing.pairing_code)
        assertEquals("A".repeat(64), pairing.certificate_sha256)
        assertEquals(4_102_444_800L, pairing.expires_at_unix)
    }
}
