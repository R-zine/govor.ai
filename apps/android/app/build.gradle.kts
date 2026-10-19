import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
}

val govorVersionCode = providers.gradleProperty("govorVersionCode").orElse("1").get().toInt()
val govorVersionName = providers.gradleProperty("govorVersionName").orElse("0.1.0").get()

android {
    namespace = "ai.govor.app"
    compileSdk = 34

    defaultConfig {
        applicationId = "ai.govor.app"
        minSdk = 26
        targetSdk = 34
        versionCode = govorVersionCode
        versionName = govorVersionName
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    val signingPropertiesPath = providers.gradleProperty("govorSigningProperties").orNull
    if (signingPropertiesPath != null) {
        val signingProperties = Properties().apply {
            file(signingPropertiesPath).inputStream().use(::load)
        }
        signingConfigs.create("release") {
            storeFile = file(requireNotNull(signingProperties.getProperty("storeFile")))
            storePassword = requireNotNull(signingProperties.getProperty("storePassword"))
            keyAlias = requireNotNull(signingProperties.getProperty("keyAlias"))
            keyPassword = requireNotNull(signingProperties.getProperty("keyPassword"))
        }
        buildTypes.getByName("release") {
            signingConfig = signingConfigs.getByName("release")
            isMinifyEnabled = false
        }
    }

    packaging {
        resources.excludes += setOf("META-INF/DEPENDENCIES", "META-INF/LICENSE*")
    }
}

kotlin {
    jvmToolchain(17)
}

dependencies {
    implementation(project(":core"))
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)
    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.webrtc.android)
    implementation(libs.okhttp)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.core.ktx)
    debugImplementation(libs.androidx.compose.ui.tooling)
}
