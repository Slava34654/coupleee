# Ассеты Flutter-порта

Папка `assets/` в этом репозитории. Что скопировать из оригинала
(`33/android/app/src/main/assets/` + `res/`):

## 1. Компаньон three.js (обязательно)

Источник: `33/android/app/src/main/assets/companion/`:

- `index.html` — оболочка сцены питомца,
- `scene.js` — процедурная сцена и персонажи (оригинальная геометрия, без внешних моделей),
- `three.min.js` — Three.js r160 (MIT, см. `THREE-LICENSE.txt`),
- `THREE-LICENSE.txt`, `NOTICE.txt` — лицензии (сохранить рядом!).

Назначение в Flutter: `WebView` на экране питомца (`pet_assets.dart` /
`CompanionScreen` → `CompanionScene`), грузит локальный `index.html`.
В `pubspec.yaml`:

```yaml
flutter:
  assets:
    - assets/companion/index.html
    - assets/companion/scene.js
    - assets/companion/three.min.js
```

## 2. Иконки приложения

Источник: `33/android/app/src/main/res/mipmap-*/ic_launcher*.png`.
В Flutter лаунчер-иконки генерируются через `flutter_launcher_icons`,
исходник — одна из `ic_launcher.png` (xxxhdpi), положенная в
`assets/icon/app_icon.png`.

## 3. Фоны виджетов (для нативной стороны)

Источник: `33/android/app/src/main/res/drawable/`:

- `widget_couple_bg.xml`, `widget_distance_bg.xml`, `widget_loading_bg.xml`,
- `res/layout/widget_loading.xml`,
- `res/xml/couple_widget_info.xml`, `distance_widget_info.xml`.

Копируются не в `assets/`, а в `android/app/src/main/res/` при создании
нативной обвязки (см. `android/README_ANDROID.md`).

## 4. Что НЕ копировать

- `couple.db`, `backend/photos/` — данные сервера, живут на бэкенде.
- `android/Enrwine.apk` — старый нативный билд, не нужен Flutter-порту.
