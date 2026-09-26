.PHONY: setup keys dev down migrate seed test smoke-test console mobile cap-build cap-open

setup:
	@echo "Setting up ScholarSetu environment..."
	@echo "Available targets: dev, down, migrate, seed, smoke-test, console, cap-build, cap-open"

keys:
	@mkdir -p services/core/secrets
	@test -f services/core/secrets/attestation_ed25519.pem \
		&& echo "Attestation key already exists (not overwritten)." \
		|| (openssl genpkey -algorithm ed25519 -out services/core/secrets/attestation_ed25519.pem \
			&& chmod 600 services/core/secrets/attestation_ed25519.pem \
			&& echo "Created services/core/secrets/attestation_ed25519.pem")

dev:
	docker-compose -f infra/docker-compose.yml -f infra/docker-compose.override.yml up --build

down:
	docker-compose -f infra/docker-compose.yml down

migrate:
	docker-compose -f infra/docker-compose.yml exec core alembic upgrade head

seed:
	docker-compose -f infra/docker-compose.yml -f infra/docker-compose.override.yml exec core python /scripts/seed_demo.py

test:
	pytest

smoke-test:
	python3 scripts/demo_smoke_test.py

console:
	cd apps/console && npm run dev

cap-build:
	cd apps/console && npm run cap:build

cap-open:
	cd apps/console && npx cap open android
