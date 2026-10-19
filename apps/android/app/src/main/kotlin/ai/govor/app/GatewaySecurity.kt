package ai.govor.app

import android.content.Context
import android.os.Build
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import org.json.JSONObject
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.security.KeyStore
import java.security.MessageDigest
import java.security.SecureRandom
import java.security.cert.CertificateException
import java.security.cert.X509Certificate
import java.util.UUID
import java.util.concurrent.TimeUnit
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import javax.net.ssl.SSLContext
import javax.net.ssl.SSLSession
import javax.net.ssl.X509TrustManager

data class GatewayCredential(
    val controlHost: String,
    val mediaHost: String,
    val certificateFingerprint: String,
    val deviceId: String,
    val credential: String,
)

class SecureGatewayCredentialStore(private val context: Context) {
    private val preferences = context.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE)

    fun load(): GatewayCredential? = runCatching {
        val encodedIv = preferences.getString(IV, null) ?: return null
        val encodedCiphertext = preferences.getString(CIPHERTEXT, null) ?: return null
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(
            Cipher.DECRYPT_MODE,
            key(),
            GCMParameterSpec(128, Base64.decode(encodedIv, Base64.NO_WRAP)),
        )
        val json = JSONObject(
            String(
                cipher.doFinal(Base64.decode(encodedCiphertext, Base64.NO_WRAP)),
                Charsets.UTF_8,
            ),
        )
        GatewayCredential(
            controlHost = json.getString("control_host"),
            mediaHost = json.getString("media_host"),
            certificateFingerprint = json.getString("certificate_fingerprint"),
            deviceId = json.getString("device_id"),
            credential = json.getString("credential"),
        )
    }.getOrNull()

    fun save(value: GatewayCredential) {
        val json = JSONObject()
            .put("control_host", value.controlHost)
            .put("media_host", value.mediaHost)
            .put("certificate_fingerprint", value.certificateFingerprint)
            .put("device_id", value.deviceId)
            .put("credential", value.credential)
            .toString()
            .toByteArray(Charsets.UTF_8)
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val ciphertext = cipher.doFinal(json)
        preferences.edit()
            .putString(IV, Base64.encodeToString(cipher.iv, Base64.NO_WRAP))
            .putString(CIPHERTEXT, Base64.encodeToString(ciphertext, Base64.NO_WRAP))
            .apply()
    }

    private fun key(): SecretKey {
        val keyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (keyStore.getKey(KEY_ALIAS, null) as? SecretKey)?.let { return it }
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        generator.init(
            KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setRandomizedEncryptionRequired(true)
                .build(),
        )
        return generator.generateKey()
    }

    private companion object {
        const val PREFERENCES = "govor_secure_gateway"
        const val KEY_ALIAS = "govor.ai.gateway.device.v1"
        const val IV = "iv"
        const val CIPHERTEXT = "ciphertext"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
    }
}

object GatewaySecurity {
    fun normalizeHost(value: String): String = value.trim()
        .removePrefix("http://")
        .removePrefix("https://")
        .removePrefix("ws://")
        .removePrefix("wss://")
        .trimEnd('/')

    fun normalizeFingerprint(value: String): String {
        val normalized = value.filter(Char::isLetterOrDigit).uppercase()
        require(normalized.length == 64 && normalized.all { it in "0123456789ABCDEF" }) {
            "Certificate fingerprint must contain 64 hexadecimal characters."
        }
        return normalized
    }

    fun pinnedClient(fingerprint: String): OkHttpClient {
        val normalized = normalizeFingerprint(fingerprint)
        val manager = FingerprintTrustManager(normalized)
        val context = SSLContext.getInstance("TLS")
        context.init(null, arrayOf(manager), SecureRandom())
        return OkHttpClient.Builder()
            .sslSocketFactory(context.socketFactory, manager)
            .hostnameVerifier { _, session -> sessionMatches(session, normalized) }
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(0, TimeUnit.MILLISECONDS)
            .build()
    }

    fun developmentClient(): OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .build()

    private fun sessionMatches(session: SSLSession, expected: String): Boolean = runCatching {
        val certificate = session.peerCertificates.first() as X509Certificate
        fingerprint(certificate) == expected
    }.getOrDefault(false)

    private fun fingerprint(certificate: X509Certificate): String = MessageDigest
        .getInstance("SHA-256")
        .digest(certificate.encoded)
        .joinToString("") { "%02X".format(it) }

    private class FingerprintTrustManager(private val expected: String) : X509TrustManager {
        override fun checkClientTrusted(chain: Array<out X509Certificate>?, authType: String?) =
            throw CertificateException("client certificates are not accepted")

        override fun checkServerTrusted(chain: Array<out X509Certificate>?, authType: String?) {
            val certificate = chain?.firstOrNull()
                ?: throw CertificateException("server certificate is missing")
            if (fingerprint(certificate) != expected) {
                throw CertificateException("server certificate fingerprint does not match")
            }
            certificate.checkValidity()
        }

        override fun getAcceptedIssuers(): Array<X509Certificate> = emptyArray()
    }
}

class GatewayPairingClient {
    fun pair(
        controlHost: String,
        mediaHost: String,
        pairingCode: String,
        certificateFingerprint: String,
    ): GatewayCredential {
        require(pairingCode.matches(Regex("^[0-9]{8}$"))) {
            "Enter the eight-digit pairing code shown on Windows."
        }
        val normalizedControl = GatewaySecurity.normalizeHost(controlHost)
        val normalizedMedia = GatewaySecurity.normalizeHost(mediaHost)
        require(normalizedControl.isNotBlank() && normalizedMedia.isNotBlank()) {
            "Enter the Windows host and ports."
        }
        val fingerprint = GatewaySecurity.normalizeFingerprint(certificateFingerprint)
        val deviceId = UUID.randomUUID().toString()
        val correlationId = UUID.randomUUID().toString()
        val body = JSONObject()
            .put("protocol_version", "1.0")
            .put("message_type", "pairing.request")
            .put("correlation_id", correlationId)
            .put(
                "payload",
                JSONObject()
                    .put("code", pairingCode)
                    .put("device_id", deviceId)
                    .put("device_name", "${Build.MANUFACTURER} ${Build.MODEL}".take(64)),
            )
            .toString()
            .toRequestBody("application/json".toMediaType())
        val client = GatewaySecurity.pinnedClient(fingerprint)
        try {
            val request = Request.Builder()
                .url("https://$normalizedControl/v1/pairing")
                .post(body)
                .build()
            client.newCall(request).execute().use { response ->
                val responseText = response.body?.string().orEmpty()
                require(response.isSuccessful) { "Pairing was rejected by the Windows host." }
                val message = JSONObject(responseText)
                require(message.getString("protocol_version") == "1.0")
                require(message.getString("message_type") == "pairing.ok")
                require(message.getString("correlation_id") == correlationId)
                val payload = message.getJSONObject("payload")
                require(payload.getString("device_id") == deviceId)
                val credential = payload.getString("credential")
                require(credential.length in 32..256)
                return GatewayCredential(
                    normalizedControl,
                    normalizedMedia,
                    fingerprint,
                    deviceId,
                    credential,
                )
            }
        } finally {
            client.dispatcher.executorService.shutdown()
            client.connectionPool.evictAll()
        }
    }
}
