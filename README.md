# Saymer — Networking & Infrastructure Projects

**EN:** Personal toolbox for home-network and VPS infrastructure: self-healing VPN gateways on Keenetic routers, DPI-aware routing with Mihomo, WARP/AmneziaWG tunnels and local-first browser config generators. Documentation is mostly in Russian.

Разрабатываю инструменты для домашней сети и VPS: превращаю роутер Keenetic с Entware в самовосстанавливающийся VPN-шлюз, автоматизирую сборку и безопасное обновление Mihomo, проектирую маршрутизацию с обходом DPI и аккуратные сценарии управления VPS — от установки до диагностики.

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
| **[link-generators](https://github.com/saymer-alt/link-generators)** · [открыть веб-версию](https://saymer-alt.github.io/link-generators/) | Браузерный генератор конфигураций Mihomo и ссылок WARP MASQUE: генерация и валидация полностью локальны, ключи не покидают браузер |
| **[keenetic-knowledge-base](https://github.com/saymer-alt/keenetic-knowledge-base)** | База знаний по Keenetic, Entware, DPI, VPN и маршрутизации: подтверждённые материалы отделены от исследований и черновиков |
| **[amnezia-mihomo-gateway](https://github.com/saymer-alt/amnezia-mihomo-gateway)** | VPS-шлюз: клиентский трафик AmneziaWG выходит в интернет через Mihomo TUN и Cloudflare WARP — реальный IP сервера остаётся скрытым |
| **[vps-gateway-bootstrap](https://github.com/saymer-alt/vps-gateway-bootstrap)** | Экспериментальный safety-first CLI для VPS: read-only диагностика (discover / doctor / validate) и dry-run-планирование; реальные изменения — только через жизненный цикл с подтверждением плана по SHA-256-отпечатку. Исследовательский проект, а не готовый автодеплой |
| **[mihomo-auto-build](https://github.com/saymer-alt/mihomo-auto-build)** | Автоматизированные сборки Mihomo для MIPSel softfloat: сборки в GitHub Actions с проверкой контрольных сумм и автоматическими релизами |

## С чего начать

- **Поднять VPN-шлюз на роутере Keenetic** → [keenetic-auto-setup](https://github.com/saymer-alt/keenetic-auto-setup): в README быстрый старт, требования к железу и памяти.
- **Собрать конфиг Mihomo, не редактируя YAML руками** → откройте [веб-генератор](https://saymer-alt.github.io/link-generators/) или его исходники — [link-generators](https://github.com/saymer-alt/link-generators).
- **Разобраться, как это устроено** → [keenetic-knowledge-base](https://github.com/saymer-alt/keenetic-knowledge-base): разборы Keenetic, Entware, DPI-обхода и VPN.
- **Спрятать IP VPS-шлюза за WARP** → [amnezia-mihomo-gateway](https://github.com/saymer-alt/amnezia-mihomo-gateway).
- **Продиагностировать VPS, не рискуя продакшеном** → [vps-gateway-bootstrap](https://github.com/saymer-alt/vps-gateway-bootstrap): по умолчанию работает в режиме только чтения.
- **Нужна сборка Mihomo под MIPSel softfloat** → готовые артефакты в [mihomo-auto-build](https://github.com/saymer-alt/mihomo-auto-build).

## Технологии и направления

- **Платформы:** Keenetic (KeeneticOS + Entware), Debian/Ubuntu на VPS, GitHub Actions CI.
- **Языки:** POSIX shell (busybox/ash), Go, ванильный JavaScript, Python для утилит.
- **Сети и VPN:** Mihomo, AmneziaWG / WireGuard, Cloudflare WARP (MASQUE), TUN-маршрутизация, policy routing, обход DPI.
- **Инфраструктура:** идемпотентные установщики, systemd / procd, Docker, watchdog'и, CI с регрессионными тестами.

## Документация и релизы

- 🌍 Работающий веб-генератор: **<https://saymer-alt.github.io/link-generators/>**
- 📖 Техническая документация link-generators: [docs/ — архитектура, руководства, контракты тестирования](https://github.com/saymer-alt/link-generators/tree/main/docs)
- 🚀 Релизы: [keenetic-auto-setup](https://github.com/saymer-alt/keenetic-auto-setup/releases) · [link-generators](https://github.com/saymer-alt/link-generators/releases) · [amnezia-mihomo-gateway](https://github.com/saymer-alt/amnezia-mihomo-gateway/releases) · [mihomo-auto-build](https://github.com/saymer-alt/mihomo-auto-build/releases)

## Принципы разработки

- **Воспроизводимость.** Детерминированные сборки, зафиксированные версии, проверяемое происхождение артефактов.
- **Проверка изменений.** Регрессионные тесты и CI перед публикацией; живые роутеры и серверы — не полигон: реальные изменения проходят отдельное подтверждение владельца.
- **Откат.** Атомарная замена файлов, бэкапы перед изменениями, автоматический rollback при провале валидации.
- **Приватность.** Генераторы работают локально и не отправляют данные наружу; в репозиториях нет секретов, ключей, адресов серверов и личных данных.

---

*Вопросы и сообщения о багах — через Issues в соответствующем репозитории.*
