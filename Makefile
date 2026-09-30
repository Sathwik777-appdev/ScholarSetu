# ScholarSetu developer commands. Run `make env keys dev` on a fresh clone, then `make seed`.
COMPOSE = docker compose --env-file .env -f infra/docker-compose.yml
DEV = $(COMPOSE) -f infra/docker-compose.override.yml

.PHONY: env demo-env keys dev up down migrate seed lint test smoke-test console console-build mobile-check

env:            ## create .env with fresh secrets (DEMO_MODE=false)
	python3 scripts/make_env.py

demo-env:       ## create .env for a local demo (DEMO_MODE=true)
	python3 scripts/make_env.py --demo

keys:           ## create the Ed25519 attestation signing key (never overwritten)
	@mkdir -p services/core/secrets
	@test -f services/core/secrets/attestation_ed25519.pem \
		&& echo "Attestation key already exists (not overwritten)." \
		|| (openssl genpkey -algorithm ed25519 -out services/core/secrets/attestation_ed25519.pem \
			&& chmod 600 services/core/secrets/attestation_ed25519.pem \
			&& echo "Created services/core/secrets/attestation_ed25519.pem")

dev:            ## run the whole stack with live code reload
	$(DEV) up --build

up:             ## run the whole stack in the background (built images, no reload)
	$(COMPOSE) up --build -d

down:
	$(COMPOSE) down

migrate:
	$(COMPOSE) exec core alembic upgrade head

seed:           ## load the demo world (Sunita, Rahul, officers) and the synthetic population
	$(COMPOSE) exec core python /scripts/seed_demo.py

lint:
	ruff check .

test:           ## backend tests; needs the compose postgres on localhost:5434
	pytest

smoke-test:     ## the 8 demo scenes against a freshly seeded demo stack
	set -a; . ./.env; set +a; python3 scripts/demo_smoke_test.py

console:
	cd apps/console && npm run dev

console-build:
	cd apps/console && npm ci && npm run lint && npm run build

mobile-check:
	cd apps/mobile && flutter pub get && flutter analyze && flutter test

cloud-status:   ## check status and billing state of ScholarSetu GCP resources
	./scripts/cloud_power.sh status

cloud-sleep:    ## suspend VM and Cloud SQL to eliminate active GCP compute billing ($0)
	./scripts/cloud_power.sh off

cloud-wake:     ## wake up VM and Cloud SQL when needed for demos or testing
	./scripts/cloud_power.sh on
