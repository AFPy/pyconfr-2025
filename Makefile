.venv:
	python3 -m venv .venv
	.venv/bin/pip install setuptools frozen-flask flask flask-weasyprint markdown2 python-slugify babel

install: .venv

static: .venv
	.venv/bin/flask --app=pyconfr freeze

serve: .venv
	@echo -e "\nHome page available at \033[0;32mhttp://localhost:5000/\033[0m\n"
	.venv/bin/flask --app=pyconfr run --debug

serve-static: .venv
	@echo -e "\nHome page available at \033[0;33mhttp://localhost:8000/index.html\033[0m\n"
	.venv/bin/python -m http.server 8000 -d build

schedule: .venv
	.venv/bin/python schedule.py

deploy: static
	rsync -vazh --delete build/2025/ pyconfr@pycon.fr:/var/www/pycon.fr/2025/

clean:
	rm -rf build .venv __pycache__

.PHONY: install static serve serve-static deploy clean
