PY ?= .venv/bin/python
.PHONY: setup app unit api ui sec smoke bdd test parallel faults evidence tooling catalog scaffold
setup:    ; ./setup.sh
app:      ; $(PY) app                                   # sobe a API + UI em http://127.0.0.1:8080
unit:     ; $(PY) -m pytest                             # base da pirâmide (test/unit)
api:      ; $(PY) -m behave --tags=@api                 # meio
ui:       ; $(PY) -m behave --tags=@ui                  # topo
sec:      ; $(PY) -m pytest test/sec                    # segurança (OWASP), transversal
smoke:    ; $(PY) -m pytest -q && $(PY) -m behave --tags=@smoke
bdd:      ; $(PY) -m behave
test: unit bdd
parallel: ; $(PY) test/scripts/run_parallel.py         # tudo em paralelo + test/reports/
faults:   ; $(PY) test/scripts/fault_injection.py
evidence: ; ./test/scripts/run_all.sh
tooling:  ; $(PY) -m pytest test/tooling
catalog:  ; $(PY) test/scripts/step_catalog.py
scaffold: ; $(PY) test/scripts/qa_scaffold.py $(SPEC)   # make scaffold SPEC=test/specs/x.md
