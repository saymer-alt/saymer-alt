# Saymer — Networking & Infrastructure Projects

**EN:** Personal toolbox for home-network and VPS infrastructure: self-healing VPN gateways on Keenetic routers, DPI-aware routing with Mihomo, WARP/AmneziaWG tunnels and local-first browser config generators. Documentation is mostly in Russian.

Разрабатываю инструменты для домашней сети и VPS: автоматизирую настройку Keenetic с Entware, сборку и обновление Mihomo, маршрутизацию VPN и диагностику серверов. Среди отдельных проектов — резервная запись видео с IP-камер на Keenetic.

![Platforms](https://img.shields.io/badge/platforms-Keenetic%20%C2%B7%20Entware%20%C2%B7%20VPS-blue)
![VPN core](https://img.shields.io/badge/VPN%20core-Mihomo-1e8a7a)
![Tunnels](https://img.shields.io/badge/tunnels-AmneziaWG%20%C2%B7%20WARP%20MASQUE-8250df)
![Shell](https://img.shields.io/badge/shell-POSIX%20ash-4EAA25?logo=gnubash&logoColor=white)
![Go](https://img.shields.io/badge/Go-1.22%2B-00ADD8?logo=go&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-vanilla-f7df1e?logo=javascript&logoColor=black)

## Основные проекты

| Проект | Что внутри |
| :--- | :--- |
| **[keenetic-auto-setup](https://github.com/saymer-alt/keenetic-auto-setup)** | Автоматическая установка Mihomo на Keenetic + Entware одной командой: watchdog самовосстановления, Doctor-диагностика, безопасный импорт конфигурации, транзакционные обновления с откатом |
| **[keenetic-nvr](https://github.com/saymer-alt/keenetic-nvr)** | Резервный RTSP-видеорегистратор на Keenetic + Entware: автономная запись IP-камер в 72-часовой архив без перекодирования (FFmpeg), watchdog для восстановления записи и необязательные уведомления через Telegram или webhook |
| **[link-generators](https://github.com/saymer-alt/link-generators)** · [открыть веб-версию](https://saymer-alt.github.io/link-generators/) | Браузерный генератор конфигураций Mihomo и ссылок WARP MASQUE: локальная сборка YAML, проверка конфигураций и предпросмотр подписок (для загрузки подписок может использоваться Cloudflare Worker) |
| **[keenetic-knowledge-base](https://github.com/saymer-alt/keenetic-knowledge-base)** · [открыть справочник](https://saymer-alt.github.io/keenetic-knowledge-base/) | База знаний по Keenetic, Entware, DPI, VPN и маршрутизации: тематические статьи, поиск и явные статусы подтверждения материалов |
| **[amnezia-mihomo-gateway](https://github.com/saymer-alt/amnezia-mihomo-gateway)** | VPS-шлюз: клиентский трафик AmneziaWG выходит в интернет через Mihomo TUN и Cloudflare WARP. Сайты видят выходной IP WARP вместо IP VPS; VPN-клиенты при этом знают адрес VPS как endpoint подключения |
| **[vps-gateway-bootstrap](https://github.com/saymer-alt/vps-gateway-bootstrap)** | Экспериментальный safety-first CLI для VPS: read-only диагностика (discover / doctor / validate) и dry-run-планирование; реальные изменения — только через жизненный цикл с подтверждением плана по SHA-256-отпечатку. Исследовательский проект, а не готовый автодеплой |
| **[entware-go](https://github.com/saymer-alt/entware-go)** | Поддерживаемый форк Entware package feed: IPK-пакеты Mihomo для нескольких архитектур, WARPSCOUT для ARM64 и другие утилиты. Сборка и публикация через GitHub Actions |

## С чего начать

- **Поднять VPN-шлюз на роутере Keenetic** → [keenetic-auto-setup](https://github.com/saymer-alt/keenetic-auto-setup): в README быстрый старт, требования к железу и памяти.
- **Организовать резервную запись IP-камер на Keenetic** → [keenetic-nvr](https://github.com/saymer-alt/keenetic-nvr): описание возможностей, требования и инструкция по установке в документации проекта.
- **Собрать конфиг Mihomo, не редактируя YAML руками** → откройте [веб-генератор](https://saymer-alt.github.io/link-generators/) или его исходники — [link-generators](https://github.com/saymer-alt/link-generators).
- **Разобраться, как это устроено** → [онлайн-справочник](https://saymer-alt.github.io/keenetic-knowledge-base/) или [исходники базы знаний](https://github.com/saymer-alt/keenetic-knowledge-base): статьи о Keenetic, Entware, DPI и VPN с поиском.
- **Выводить клиентский трафик VPS через WARP** → [amnezia-mihomo-gateway](https://github.com/saymer-alt/amnezia-mihomo-gateway): сайты видят IP WARP, но адрес VPS не скрывается от VPN-клиентов.
- **Продиагностировать VPS, не рискуя продакшеном** → [vps-gateway-bootstrap](https://github.com/saymer-alt/vps-gateway-bootstrap): по умолчанию работает в режиме только чтения.
- **Нужны готовые IPK-пакеты Mihomo для Entware или WARPSCOUT для ARM64** → [entware-go](https://github.com/saymer-alt/entware-go), [актуальный релиз `latest`](https://github.com/saymer-alt/entware-go/releases/tag/latest).

## Технологии и направления

- **Платформы:** Keenetic (KeeneticOS + Entware), Debian/Ubuntu на VPS, GitHub Actions CI.
- **Языки:** POSIX shell (busybox/ash), Go, ванильный JavaScript, Python для утилит.
- **Сети и VPN:** Mihomo, AmneziaWG / WireGuard, Cloudflare WARP (MASQUE), TUN-маршрутизация, policy routing, обход DPI.
- **Инфраструктура:** идемпотентные установщики, systemd / procd, Docker, watchdog'и, FFmpeg/RTSP-архивирование, CI с регрессионными тестами.

## Документация и релизы

- 🌍 Работающий веб-генератор: **<https://saymer-alt.github.io/link-generators/>**
- 📖 Техническая документация link-generators: [docs/ — архитектура, руководства, контракты тестирования](https://github.com/saymer-alt/link-generators/tree/main/docs)
- 📚 [Сайт базы знаний (поиск и разделы)](https://saymer-alt.github.io/keenetic-knowledge-base/) · [Каталог исходных статей](https://github.com/saymer-alt/keenetic-knowledge-base/blob/main/docs/README.md) · [Документация Keenetic NVR v2.4](https://github.com/saymer-alt/keenetic-nvr/blob/main/NVR/v2/README.md)
- 🚀 Релизы: [keenetic-auto-setup](https://github.com/saymer-alt/keenetic-auto-setup/releases) · [link-generators](https://github.com/saymer-alt/link-generators/releases) · [amnezia-mihomo-gateway](https://github.com/saymer-alt/amnezia-mihomo-gateway/releases) · [entware-go](https://github.com/saymer-alt/entware-go/releases/tag/latest)

## Принципы разработки

- **Воспроизводимость.** Детерминированные сборки, зафиксированные версии, проверяемое происхождение артефактов.
- **Проверка изменений.** Регрессионные тесты и CI перед публикацией; живые роутеры и серверы — не полигон: реальные изменения проходят отдельное подтверждение владельца.
- **Откат.** Атомарная замена файлов, бэкапы перед изменениями, автоматический rollback при провале валидации.
- **Приватность.** Разбор ссылок и сборка конфигураций в генераторе выполняются локально. Предпросмотр подписок может обращаться к серверу подписки через промежуточный Cloudflare Worker, а диагностика — напрямую к указанному пользователем Mihomo Controller. Подробности и ограничения: [модель данных и сети](https://github.com/saymer-alt/link-generators/blob/main/docs/DATAFLOW.md).

---

*Вопросы и сообщения о багах — через Issues в соответствующем репозитории.*
