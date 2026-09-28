# infra/

Hạ tầng chạy hệ thống, tách khỏi code ứng dụng:

- `postgres/init.sql` — bật extension `vector`, `unaccent` (spec 01 FR-05).
- `docker/` — Dockerfile môi trường chạy ứng dụng (architecture §6).

`docker-compose.yml` nằm ở gốc repo để `make up` / `docker compose` dùng trực tiếp.
