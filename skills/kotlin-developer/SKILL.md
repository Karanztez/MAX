---
name: Kotlin Developer
description: พัฒนา ออกแบบ และสร้างโปรเจกต์ Kotlin (Android, KMP, Coroutines, Compose, Gradle Kotlin DSL, Spring Boot)
default: false
---

# Kotlin Development Skill (MAX Agent)

ทักษะสำหรับการพัฒนาโปรเจกต์ภาษา **Kotlin** ครอบคลุม Kotlin 2.0+, การใช้งาน Coroutines & Flow, การพัฒนา Android ด้วย Jetpack Compose, Kotlin Multiplatform (KMP), และการคอมไพล์/รันทั้งบน Desktop, Server และ Android Termux

---

## 1. โครงสร้างโปรเจกต์ Kotlin มาตรฐาน (Gradle Kotlin DSL)

### Standard Layout:
```
my-kotlin-app/
├── build.gradle.kts
├── settings.gradle.kts
├── gradlew
├── gradlew.bat
└── src/
    ├── main/
    │   ├── kotlin/
    │   │   └── com/example/app/
    │   │       ├── Main.kt
    │   │       └── models/
    │   └── resources/
    └── test/
        └── kotlin/
            └── com/example/app/
                └── AppTest.kt
```

### ตัวอย่าง `build.gradle.kts` ขั้นพื้นฐาน:
```kotlin
plugins {
    kotlin("jvm") version "2.0.0"
    application
}

repositories {
    mavenCentral()
}

dependencies {
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.8.1")
    testImplementation(kotlin("test"))
}

application {
    mainClass.set("com.example.app.MainKt")
}
```

---

## 2. การคอมไพล์และรันโค้ด Kotlin ผ่าน Terminal / Shell

### 🚀 Standalone Script หรือ Single File:
```bash
# คอมไพล์ไฟล์ .kt เป็น JAR
kotlinc src/com/example/app/Main.kt -include-runtime -d app.jar

# รันไฟล์ JAR
java -jar app.jar

# รัน Kotlin Script (.kts) ทันที
kotlinc -script script.main.kts
```

### 🐘 Gradle Kotlin Projects:
```bash
# รันโปรเจกต์
./gradlew run

# รัน Tests
./gradlew test

# บิลด์ JAR
./gradlew build
```

---

## 3. การใช้งาน Kotlin บน Android (Termux)

บน Termux สามารถติดตั้งคอมไพเลอร์ Kotlin และ OpenJDK เพื่อเขียนและรันได้ทันที:
```bash
# 1. ติดตั้ง openjdk และ kotlin บน Termux
pkg update && pkg install -y openjdk-17 kotlin

# 2. ตรวจสอบเวอร์ชัน
kotlinc -version

# 3. สร้างและรันโปรแกรม Kotlin ในโฟลเดอร์ปัจจุบัน
cat << 'EOF' > Hello.kt
fun main() {
    println("⚡ Hello from Kotlin on Termux!")
}
EOF

kotlinc Hello.kt -include-runtime -d Hello.jar
java -jar Hello.jar
```

---

## 4. แนวปฏิบัติและรูปแบบที่แนะนำ (Kotlin Idioms)
1. **Null Safety:** ใช้ Safe Calls (`?.`), Elvis Operator (`?:`), และหลีกเลี่ยง Non-null Assertion (`!!`)
2. **Data & Sealed Classes:** ใช้ `data class` สำหรับ DTOs/Value Objects และ `sealed interface` / `sealed class` สำหรับ State Management และ Result types
3. **Coroutines & Flow:** ใช้ `suspend functions` และ `CoroutineScope` ที่มี Structured Concurrency สำหรับงาน Asynchronous / I/O
4. **Extension Functions:** ใช้ส่วนต่อขยายฟังก์ชันเพื่อเพิ่มความกระชับและอ่านง่ายของโค้ด
