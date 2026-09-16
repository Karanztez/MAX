---
name: Java Developer
description: พัฒนา ออกแบบ และสร้างโปรเจกต์ Java (Maven, Gradle, Spring Boot, Android, CLI) พร้อมคำสั่งคอมไพล์และรัน
default: false
---

# Java Development Skill (MAX Agent)

ทักษะสำหรับการพัฒนาโปรเจกต์ภาษา **Java** ครอบคลุมตั้งแต่การออกแบบสถาปัตยกรรม (Architecture), การเขียนโค้ด (Clean Code & OOP), การจัดการ Build Tools (Gradle / Maven), ไปจนถึงการคอมไพล์และรันบนทุกระบบปฏิบัติการ (Windows, Linux, macOS และ Android Termux)

---

## 1. การสร้างและจัดการโครงสร้างโปรเจกต์ (Standard Project Layout)

### Standard Maven / Gradle Structure

```text
my-java-app/
├── pom.xml (หรือ build.gradle / build.gradle.kts)
├── src/
│   ├── main/
│   │   ├── java/
│   │   │   └── com/example/app/
│   │   │       └── Main.java
│   │   └── resources/
│   │       └── application.properties
│   └── test/
│       └── java/
│           └── com/example/app/
│               └── AppTest.java
└── README.md
```

---

## 2. การคอมไพล์และรันโค้ด Java ผ่าน Terminal / Shell

### ☕ Single File หรือ Standalone Java (Java 11+ / 17 / 21)

```bash
# รันไฟล์ .java ได้ทันทีโดยไม่ต้องคอมไพล์ล่วงหน้า (Java 11+)
java src/com/example/app/Main.java

# คอมไพล์เป็น .class แล้วรัน
javac -d bin src/com/example/app/Main.java
java -cp bin com.example.app.Main
```

### 🐘 Gradle Projects

```bash
# คอมไพล์และรันโปรเจกต์
./gradlew run

# รัน Unit Tests
./gradlew test

# บิลด์เป็น JAR File
./gradlew build
# รันไฟล์ JAR ที่ได้
java -jar build/libs/my-app-1.0.0.jar
```

### 📦 Maven Projects

```bash
# คอมไพล์และรัน
mvn clean compile
mvn exec:java -Dexec.mainClass="com.example.app.Main"

# บิลด์แพ็กเกจ JAR
mvn clean package
java -jar target/my-app-1.0.0.jar
```

---

## 3. การใช้งาน Java บน Android (Termux)

บน Termux สามารถติดตั้งและใช้งาน OpenJDK ได้เต็มรูปแบบ:

```bash
# 1. ติดตั้ง OpenJDK (Java 17 / 21)
pkg update && pkg install -y openjdk-17

# 2. ตรวจสอบเวอร์ชัน
java -version
javac -version

# 3. สร้างและรันโปรแกรม Java ในโฟลเดอร์ปัจจุบัน
mkdir -p src && cat << 'EOF' > src/Hello.java
public class Hello {
    public static void main(String[] args) {
        System.out.println("Hello from Java on Termux!");
    }
}
EOF

javac src/Hello.java
java -cp src Hello
```

---

## 4. แนวปฏิบัติที่ดีในการเขียนโค้ด Java (Best Practices)

1. **Modern Java Features:** ใช้ `record`, `sealed class`, `pattern matching`, `var`, `Stream API`, และ `Optional` อย่างเหมาะสม
2. **Robust Error Handling:** จัดการ Exception อย่างชัดเจน ไม่ swallow exception ด้วย empty catch block
3. **Threading & Concurrency:** ใช้ `Virtual Threads` (Java 21+) หรือ `ExecutorService` หลีกเลี่ยงการสร้าง raw `Thread` แบบไม่ควบคุม
4. **Dependency Management:** ระบุเวอร์ชันและ scope ให้ชัดเจนใน `pom.xml` หรือ `build.gradle`
