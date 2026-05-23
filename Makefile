.PHONY: skills clean verify install-claude install-cursor

skills:
	python build_skills.py

clean:
	rm -rf dist/

verify:
	python build_skills.py --verify

install-claude:
	@echo "Copiando dist/claude/skills/* a ~/.claude/skills/ (modo global)"
	mkdir -p $$HOME/.claude/skills
	cp -R dist/claude/skills/* $$HOME/.claude/skills/

install-cursor:
	@echo "Copiando dist/cursor/.cursor/rules/* a .cursor/rules/ del proyecto actual"
	mkdir -p .cursor/rules
	cp -R dist/cursor/.cursor/rules/* .cursor/rules/
