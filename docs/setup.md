# Setup

## Requirements

- JDK 21
- Gradle 8+
- Paper server matching the target Minecraft version

## Build

```sh
gradle build
```

## Local Server

Place the Paper server jar in `server/`, accept the EULA in `server/eula.txt`, and copy built module jars into `server/plugins/`.
