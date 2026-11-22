"""End-to-end tests for the Power BI Workspaces CLI. Standard library only.

    python -m unittest discover -s _sistema/testes -v
"""

from __future__ import annotations

import io
import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "_sistema"))

from workspaces import caminhos, cli, layout, pbit, prototipo, secrets, tmdl  # noqa: E402
from workspaces import skill as skill_mod  # noqa: E402
from workspaces.sqlsync import select_aliases  # noqa: E402
from workspaces.util import m_string, pascal, slugify  # noqa: E402


def make_pbit(path: Path) -> None:
    """A tiny but realistic .pbit: legacy layout + model with classic anti-patterns."""
    model = {
        "name": "Legacy",
        "compatibilityLevel": 1550,
        "model": {
            "culture": "pt-BR",
            "tables": [
                {
                    "name": "Vendas",
                    "columns": [
                        {"name": "id_cliente", "dataType": "int64", "sourceColumn": "id_cliente"},
                        {"name": "Data", "dataType": "dateTime", "sourceColumn": "Data"},
                        {"name": "Valor", "dataType": "double", "sourceColumn": "Valor"},
                        {"name": "Observacao", "dataType": "string", "sourceColumn": "Observacao"},
                        {"name": "Margem", "dataType": "double", "type": "calculated",
                         "expression": "Vendas[Valor] * 0.2"},
                    ],
                    "partitions": [{"name": "Vendas", "mode": "import", "source": {"type": "m", "expression": [
                        "let",
                        '    Fonte = Sql.Database("10.0.0.15", "ERP"),',
                        '    Tab = Fonte{[Schema="dbo",Item="vendas"]}[Data],',
                        '    Tipos = Table.TransformColumnTypes(Tab,{{"Valor", type number}}),',
                        '    Filtro = Table.SelectRows(Tipos, each [Valor] > 0)',
                        "in",
                        "    Filtro"]}}],
                    "measures": [{"name": "Total Vendas", "expression": "SUM(Vendas[Valor])"}],
                },
                {
                    "name": "Clientes",
                    "columns": [
                        {"name": "id_cliente", "dataType": "int64", "sourceColumn": "id_cliente"},
                        {"name": "Nome", "dataType": "string", "sourceColumn": "Nome"},
                        {"name": "Telefone", "dataType": "string", "sourceColumn": "Telefone"},
                    ],
                    "partitions": [{"name": "Clientes", "mode": "import", "source": {
                        "type": "m", "expression": 'let Fonte = Sql.Database("10.0.0.15", "ERP") in Fonte'}}],
                },
                {"name": "LocalDateTable_123", "isHidden": True, "columns": [], "partitions": []},
            ],
            "relationships": [
                {"name": "r1", "fromTable": "Vendas", "fromColumn": "id_cliente", "toTable": "Clientes",
                 "toColumn": "id_cliente", "crossFilteringBehavior": "bothDirections"},
            ],
        },
    }
    visual_cfg = {"singleVisual": {"visualType": "clusteredBarChart", "prototypeQuery": {"Select": [
        {"Column": {"Expression": {"SourceRef": {"Source": "c"}}, "Property": "Nome"}, "Name": "Clientes.Nome"},
        {"Measure": {"Expression": {"SourceRef": {"Source": "v"}}, "Property": "Total Vendas"},
         "Name": "Vendas.Total Vendas"}]},
        "projections": {"Category": [{"queryRef": "Clientes.Nome"}], "Y": [{"queryRef": "Vendas.Total Vendas"}]}}}
    layout = {"sections": [{"name": "s1", "displayName": "Resumo", "ordinal": 0, "width": 1280, "height": 720,
                            "visualContainers": [{"x": 0, "y": 0, "width": 400, "height": 300,
                                                  "config": json.dumps(visual_cfg)}]}]}
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("DataModelSchema", json.dumps(model).encode("utf-16-le"))
        z.writestr("Report/Layout", json.dumps(layout).encode("utf-16-le"))
        z.writestr("Version", "1.28".encode("utf-16-le"))


class Sandbox(unittest.TestCase):
    """Copies the repo skeleton (no dashboards) to a temp folder."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="pbw-test-"))
        for item in ("_sistema", "conexoes", "identidade-visual", "refatorar"):
            shutil.copytree(REPO / item, self.tmp / item, ignore=shutil.ignore_patterns("__pycache__", "testes"))
        shutil.copy(REPO / "workspaces.toml", self.tmp / "workspaces.toml")
        (self.tmp / "dashboards").mkdir()
        (self.tmp / "dashboards" / "LEIA-ME.md").write_text("# dashboards\n", encoding="utf-8")
        self._cwd = Path.cwd()
        import os
        os.chdir(self.tmp)

    def tearDown(self) -> None:
        import os
        os.chdir(self._cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_cli(self, *args: str) -> tuple[int, str]:
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(buf):
            code = cli.main(list(args))
        return code, buf.getvalue()


class TestHelpers(unittest.TestCase):
    def test_slug_and_pascal(self) -> None:
        self.assertEqual(slugify("Contas a Receber"), "contas-a-receber")
        self.assertEqual(slugify("  Gestão  de Frota / 2026 "), "gestao-de-frota-2026")
        self.assertEqual(pascal("Aging de Títulos"), "AgingDeTitulos")

    def test_m_string_escapes(self) -> None:
        self.assertEqual(m_string('SELECT "a"\nFROM t'), '"SELECT ""a""#(lf)FROM t"')
        self.assertEqual(m_string("x #(lf) y"), '"x #(#)(lf) y"')

    def test_select_aliases(self) -> None:
        sql = "SELECT a.id AS id, CAST(x AS date) AS [Data], SUM(v) total FROM t GROUP BY a.id"
        self.assertEqual(select_aliases(sql), ["id", "Data", "total"])
        self.assertIsNone(select_aliases("SELECT * FROM t"))


class TestNewDashboard(Sandbox):
    def test_new_validate_and_sync(self) -> None:
        code, out = self.run_cli("novo", "Acme/Comercial/Vendas/Painel de Vendas")
        self.assertEqual(code, 0, out)
        dash = self.tmp / "dashboards/acme/comercial/vendas/painel-de-vendas"
        self.assertTrue((dash / "2-power-bi/PainelDeVendas.pbip").exists())   # ready to open
        self.assertEqual(sorted(p.name for p in dash.iterdir()),
                         ["1-seu-pedido", "2-power-bi", "3-entrega", "LEIA-ME.md", "trabalho-da-ia"])
        for f in ("1-seu-pedido/PEDIDO.md", "1-seu-pedido/anexos/consultas-sql",
                  "1-seu-pedido/anexos/imagens-e-rascunhos", "1-seu-pedido/anexos/documentos", "trabalho-da-ia/ficha.toml",
                  "trabalho-da-ia/desenho.md", "trabalho-da-ia/conferencia.md", "trabalho-da-ia/sql/LEIA-ME.md"):
            self.assertTrue((dash / f).exists(), f)
        pedido = (dash / "1-seu-pedido/PEDIDO.md").read_text(encoding="utf-8")
        self.assertIn("Regras de negócio", pedido)
        self.assertIn("Visuais que eu quero", pedido)
        pages = [json.loads(p.read_text(encoding="utf-8"))["displayName"]
                 for p in dash.glob("2-power-bi/*.Report/definition/pages/*/page.json")]
        self.assertEqual(sorted(pages), ["Documentação", "Visão Geral"])  # prototype + documentation
        # add a SQL file and sync -> stub table is created with parameters (not hardcoded host)
        (dash / "trabalho-da-ia/sql/Fato Vendas.sql").write_text(
            "-- @description: vendas\nSELECT id AS id, valor AS [Valor] FROM bi.vendas", encoding="utf-8")
        code, out = self.run_cli("sincronizar-sql", "painel-de-vendas")     # by name
        self.assertEqual(code, 0, out)
        t = (dash / "2-power-bi/PainelDeVendas.SemanticModel/definition/tables/Fato Vendas.tmdl").read_text(encoding="utf-8")
        self.assertIn("Sql.Database(Erp_Server, Erp_Database)", t)
        self.assertIn("EnableFolding = true", t)
        # stub without columns must fail validation (PBW023)
        code, out = self.run_cli("validar", str(dash))
        self.assertEqual(code, 1)
        self.assertIn("PBW023", out)

    def test_english_aliases_still_work(self) -> None:
        code, out = self.run_cli("new", "Acme/Comercial/Vendas/Painel")
        self.assertEqual(code, 0, out)
        code, out = self.run_cli("open", "painel", "--so-caminho")
        self.assertEqual(code, 0, out)
        self.assertIn("Painel.pbip", out)

    def test_connect_switches_profile(self) -> None:
        self.run_cli("novo", "Acme/Comercial/Vendas/Painel")
        dash = self.tmp / "dashboards/acme/comercial/vendas/painel"
        (dash / "trabalho-da-ia/sql/Fato.sql").write_text("SELECT 1 AS x FROM y", encoding="utf-8")
        code, out = self.run_cli("conectar", str(dash), "-c", "bigquery.example")
        self.assertEqual(code, 0, out)
        exprs = (dash / "2-power-bi/Painel.SemanticModel/definition/expressions.tmdl").read_text(encoding="utf-8")
        self.assertIn("Gcp_BillingProject", exprs)
        self.assertNotIn("Erp_Server", exprs)
        t = (dash / "2-power-bi/Painel.SemanticModel/definition/tables/Fato.tmdl").read_text(encoding="utf-8")
        self.assertIn("GoogleBigQuery.Database", t)

    def test_rejects_wrong_depth(self) -> None:
        code, out = self.run_cli("novo", "Acme/Vendas/Painel")
        self.assertEqual(code, 1)
        self.assertIn("4 níveis", out)


class TestPrototype(Sandbox):
    DESIGN = """# Desenho
## 3. Páginas
### Visão Geral
**Pergunta:** quanto vendemos?
| Zona | Visual | Campos |
|---|---|---|
| KPIs | Cartão | [Atualizado em] |
| KPIs | Cartão | [Vendas] |
| Tendência | Colunas | Calendario[Ano-Mês] × [Vendas] |
| Filtro | Segmentação | Dim Loja[Regional] |
| Detalhe | Tabela | Pedidos |
### Clientes
| Zona | Visual | Campos |
|---|---|---|
| Explicação | Barras | Cliente × [Vendas] |
### Documentação (obrigatória)
gerada
## 4. Decisões
"""

    def _pages(self, dash: Path) -> dict[str, list[dict]]:
        out = {}
        for pj in dash.glob("2-power-bi/*.Report/definition/pages/*/page.json"):
            name = json.loads(pj.read_text(encoding="utf-8"))["displayName"]
            out[name] = [json.loads(v.read_text(encoding="utf-8")) for v in pj.parent.glob("visuals/*/visual.json")]
        return out

    def test_parse_design(self) -> None:
        pages = prototipo.parse_design(self.DESIGN)
        self.assertEqual([p.name for p in pages], ["Visão Geral", "Clientes"])     # doc page skipped
        self.assertEqual(pages[0].question, "quanto vendemos?")
        self.assertEqual([i.zone for i in pages[0].items], ["kpis", "kpis", "main", "filters", "detail"])

    def test_prototype_pages_open_and_are_replaceable(self) -> None:
        self.run_cli("novo", "Acme/Comercial/Vendas/Painel")
        dash = self.tmp / "dashboards/acme/comercial/vendas/painel"
        (dash / "trabalho-da-ia/desenho.md").write_text(self.DESIGN, encoding="utf-8")
        code, out = self.run_cli("prototipo", "painel")
        self.assertEqual(code, 0, out)
        pages = self._pages(dash)
        self.assertEqual(set(pages), {"Visão Geral", "Clientes", "Documentação"})
        types = [v["visual"]["visualType"] for v in pages["Visão Geral"]]
        self.assertIn("card", types)                     # [Atualizado em] exists in the model -> real card
        for vis in pages["Visão Geral"]:                 # everything inside the 1280x720 canvas
            pos = vis["position"]
            self.assertLessEqual(pos["x"] + pos["width"], 1280)
            self.assertLessEqual(pos["y"] + pos["height"], 720)
        order = json.loads(next(dash.glob("2-power-bi/*.Report/definition/pages/pages.json")).read_text(encoding="utf-8"))
        names = {pj.parent.name: json.loads(pj.read_text(encoding="utf-8"))["displayName"]
                 for pj in dash.glob("2-power-bi/*.Report/definition/pages/*/page.json")}
        self.assertEqual([names[p] for p in order["pageOrder"]], ["Visão Geral", "Clientes", "Documentação"])
        # a page rebuilt for real (no PROTÓTIPO marker) is kept on the next run
        clientes = next(pj.parent for pj in dash.glob("2-power-bi/*.Report/definition/pages/*/page.json")
                        if names[pj.parent.name] == "Clientes")
        for v in clientes.glob("visuals/*/visual.json"):
            v.write_text(v.read_text(encoding="utf-8").replace("PROTÓTIPO", "REAL"), encoding="utf-8")
        code, out = self.run_cli("prototipo", "painel")
        self.assertIn("mantida", out)
        self.assertTrue(clientes.exists())
        code, out = self.run_cli("validar", "painel")
        self.assertIn("PBW024", out)                     # prototype pages reported
        self.assertNotIn("PBW007", out)

    def test_broken_pbip_is_an_error(self) -> None:
        self.run_cli("novo", "Acme/Comercial/Vendas/Painel")
        dash = self.tmp / "dashboards/acme/comercial/vendas/painel"
        (dash / "2-power-bi/Painel.pbip").write_text('{"artifacts": [{"report": {"path": "Outro.Report"}}]}', encoding="utf-8")
        code, out = self.run_cli("validar", "painel")
        self.assertEqual(code, 1)
        self.assertIn("PBW007", out)
        (dash / "2-power-bi/Painel.pbip").unlink()
        code, out = self.run_cli("validar", "painel")
        self.assertIn("exatamente 1 .pbip", out)

    def test_stray_file_points_to_anexos(self) -> None:
        self.run_cli("novo", "Acme/Comercial/Vendas/Painel")
        dash = self.tmp / "dashboards/acme/comercial/vendas/painel"
        (dash / "meu-print.png").write_bytes(b"x")
        code, out = self.run_cli("validar", "painel")
        self.assertEqual(code, 1)
        self.assertIn("1-seu-pedido/anexos", out)


class TestTemplateDashboard(Sandbox):
    def test_copy_rename_and_adopt(self) -> None:
        self.run_cli("novo", "Nome da Empresa/Nome da Area/Nome da Subarea/Nome do Dashboard")
        tpl = self.tmp / "dashboards/nome-da-empresa"
        code, out = self.run_cli("validar")
        self.assertEqual(code, 0, out)                                   # the template is never validated
        self.assertNotIn("Nome do Dashboard", (self.tmp / "dashboards/CATALOGO.md").read_text(encoding="utf-8"))
        # the analyst duplicates and renames the folders, then fills the request
        dest = self.tmp / "dashboards/acme/comercial/vendas/painel-de-vendas"
        shutil.copytree(tpl / "nome-da-area/nome-da-subarea/nome-do-dashboard", dest)
        pedido = dest / "1-seu-pedido/PEDIDO.md"
        pedido.write_text(pedido.read_text(encoding="utf-8") + "\nMINHA REGRA\n", encoding="utf-8")
        (dest / "1-seu-pedido/anexos/consultas-sql/vendas.sql").write_text("SELECT 1", encoding="utf-8")
        code, out = self.run_cli("validar", str(dest))
        self.assertEqual(code, 1)
        self.assertIn("copiada do modelo", out)
        code, out = self.run_cli("novo", "Acme/Comercial/Vendas/Painel de Vendas")
        self.assertEqual(code, 0, out)
        text = pedido.read_text(encoding="utf-8")
        self.assertIn("MINHA REGRA", text)                                # the request is kept
        self.assertIn("# Pedido — Painel de Vendas", text)
        self.assertTrue((dest / "1-seu-pedido/anexos/consultas-sql/vendas.sql").exists())
        self.assertTrue((dest / "2-power-bi/PainelDeVendas.pbip").exists())
        self.assertFalse((dest / "2-power-bi/NomeDoDashboard.pbip").exists())
        code, out = self.run_cli("validar", str(dest))
        self.assertEqual(code, 0, out)

class TestWelcome(Sandbox):
    def ask(self) -> str:
        code, out = self.run_cli("boas-vindas", "--verificar")
        self.assertEqual(code, 0, out)
        return out.split()[0]

    def test_tour_is_offered_until_more_than_one_own_dashboard(self) -> None:
        self.assertEqual(self.ask(), "PERGUNTAR")                                   # raw repository
        self.run_cli("novo", "Nome da Empresa/Nome da Area/Nome da Subarea/Nome do Dashboard")
        self.run_cli("novo", "Acme/Exemplo/Exemplo/Exemplo")
        ficha = self.tmp / "dashboards/acme/exemplo/exemplo/exemplo/trabalho-da-ia/ficha.toml"
        ficha.write_text(ficha.read_text(encoding="utf-8").replace('origin = "new"', 'example = true\norigin = "new"'),
                         encoding="utf-8")
        self.assertEqual(self.ask(), "PERGUNTAR")                                   # template + example do not count
        self.run_cli("novo", "Acme/Comercial/Vendas/Painel A")
        self.assertEqual(self.ask(), "PERGUNTAR")                                   # 1 dashboard: still asks
        ph = self.tmp / "refatorar/nome-da-empresa/nome-da-area/nome-da-subarea/nome-do-dashboard"
        make_pbit(ph / "x.pbit")
        self.assertEqual(self.ask(), "PERGUNTAR")                                   # pbit in a template folder
        legacy = self.tmp / "refatorar/acme/financeiro/cobranca/aging"
        legacy.mkdir(parents=True)
        make_pbit(legacy / "Aging.pbit")
        self.assertEqual(self.ask(), "NAO-PERGUNTAR")                               # 1 dashboard + 1 legacy
        code, out = self.run_cli("boas-vindas", "--hook")
        self.assertIn('"hookEventName": "SessionStart"', out)

class TestVisualStandard(Sandbox):
    def test_app_shell_and_company_theme(self) -> None:
        from workspaces import shell
        from workspaces.util import stable_id
        self.run_cli("novo", "Acme/Comercial/Vendas/Painel")
        dash = self.tmp / "dashboards/acme/comercial/vendas/painel"
        rep = next(dash.glob("2-power-bi/*.Report"))
        for pj in rep.glob("definition/pages/*/page.json"):
            pid = pj.parent.name
            shell_ids = {stable_id(pid, k) for k in shell._keys()}
            names = {v.parent.name for v in pj.parent.glob("visuals/*/visual.json")}
            self.assertIn(stable_id(pid, "shell-sidebar"), names)             # sidebar on every page
            for vj in pj.parent.glob("visuals/*/visual.json"):
                if vj.parent.name in shell_ids:
                    continue
                x = json.loads(vj.read_text(encoding="utf-8"))["position"]["x"]
                self.assertGreaterEqual(x, shell.SIDEBAR_W)                    # content right of the sidebar
        report = json.loads((rep / "definition/report.json").read_text(encoding="utf-8"))
        self.assertNotIn("baseTheme", report["themeCollection"])              # no Microsoft base theme
        self.assertFalse((rep / "StaticResources/SharedResources").exists())
        theme = json.loads((rep / "StaticResources/RegisteredResources/acme-theme.json").read_text(encoding="utf-8"))
        self.assertFalse(theme["visualStyles"]["*"]["*"]["valueAxis"][0]["gridlineShow"])

class TestIdentity(Sandbox):
    def test_company_identity_applies_to_all_its_dashboards(self) -> None:
        self.run_cli("novo", "Nova/Comercial/Vendas/Painel A")         # company without identity -> padrao
        dash = self.tmp / "dashboards/nova/comercial/vendas/painel-a"
        report = json.loads(next(dash.glob("2-power-bi/*.Report/definition/report.json")).read_text(encoding="utf-8"))
        self.assertEqual(report["themeCollection"]["customTheme"]["name"], "padrao-theme.json")
        # the analyst creates the company identity (the AI fills trabalho-da-ia/identidade.toml)
        shutil.copytree(self.tmp / "identidade-visual/acme", self.tmp / "identidade-visual/nova")
        code, out = self.run_cli("identidade", "nova")
        self.assertEqual(code, 0, out)
        self.assertIn("painel-a", out)
        report = json.loads(next(dash.glob("2-power-bi/*.Report/definition/report.json")).read_text(encoding="utf-8"))
        self.assertEqual(report["themeCollection"]["customTheme"]["name"], "nova-theme.json")
        reg = next(dash.glob("2-power-bi/*.Report/StaticResources/RegisteredResources"))
        self.assertEqual([f.name for f in reg.iterdir()], ["nova-theme.json"])
        self.run_cli("novo", "Nova/Comercial/Vendas/Painel B")         # new dashboards get it directly
        dash_b = self.tmp / "dashboards/nova/comercial/vendas/painel-b"
        self.assertTrue(next(dash_b.glob("2-power-bi/*.Report/StaticResources/RegisteredResources/nova-theme.json")))


class TestRefactor(Sandbox):
    def test_pbit_extraction_and_refactor(self) -> None:
        inbox = self.tmp / "refatorar/acme/financeiro/contas-a-receber/aging"
        inbox.mkdir(parents=True)
        make_pbit(inbox / "Aging.pbit")
        (inbox / "notas.md").write_text("O financeiro usa este relatório toda segunda.", encoding="utf-8")
        code, out = self.run_cli("refatorar")
        self.assertEqual(code, 0, out)
        dash = self.tmp / "dashboards/acme/financeiro/contas-a-receber/aging"
        self.assertTrue((dash / "2-power-bi/Aging.pbip").exists())                   # openable right away
        legacy = dash / "trabalho-da-ia/legado"
        self.assertTrue((legacy / "original.pbit").exists())
        self.assertTrue((legacy / "PLANO.md").exists())
        summary = (legacy / "extracao/summary.md").read_text(encoding="utf-8")
        self.assertIn("Auto date/time", summary)
        self.assertIn("bidirecional", summary)
        self.assertIn("etapas de Power Query", summary)
        self.assertIn("Observacao", summary)  # unused column detected
        self.assertIn("Telefone", summary)
        pq = (legacy / "extracao/power-query.md").read_text(encoding="utf-8")
        self.assertNotIn("10.0.0.15", pq)  # redacted
        self.assertTrue((dash / "1-seu-pedido/anexos/documentos/legado-notas.md").exists())
        self.assertFalse(inbox.exists())  # inbox cleaned

        data = json.loads((legacy / "extracao/extraction.json").read_text(encoding="utf-8"))
        self.assertEqual(data["analysis"]["fact_tables"], ["Vendas"])

    def test_placeholder_path_is_not_refactored(self) -> None:
        ph = self.tmp / "refatorar/nome-da-empresa/nome-da-area/nome-da-subarea/nome-do-dashboard"
        self.assertTrue(ph.is_dir())                                   # ships with the repository
        make_pbit(ph / "Antigo.pbit")
        code, out = self.run_cli("refatorar")
        self.assertIn("renomeie as pastas", out)
        self.assertFalse((self.tmp / "dashboards/nome-da-empresa").exists())


class TestSecurity(Sandbox):
    def test_scanner_blocks_secrets_and_data(self) -> None:
        (self.tmp / "a.sql").write_text("-- conn: Server=x;User Id=sa;Password=SuperSecret1;\n", encoding="utf-8")  # pbw:allow-secret
        (self.tmp / "b.pbix").write_bytes(b"PK\x03\x04data")
        (self.tmp / "conexoes/erp.local.toml").write_text("[parameters]\n", encoding="utf-8")
        hits = secrets.scan(self.tmp, files=[self.tmp / "a.sql", self.tmp / "b.pbix",
                                             self.tmp / "conexoes/erp.local.toml"])
        rules = {h.rule for h in hits}
        self.assertIn("SEC001", rules)
        self.assertIn("SEC101", rules)
        self.assertIn("SEC102", rules)

    def test_allow_marker(self) -> None:
        (self.tmp / "doc.md").write_text("Password=example123 pbw:allow-secret\n", encoding="utf-8")
        self.assertEqual(secrets.scan(self.tmp, files=[self.tmp / "doc.md"]), [])


class TestTmdl(unittest.TestCase):
    def test_example_model_parses(self) -> None:
        defs = list((REPO / "dashboards").glob("*/*/*/*/2-power-bi/*.SemanticModel/definition"))
        self.assertTrue(defs, "example dashboard missing")
        model = tmdl.parse_model(defs[0])
        names = {t.name for t in model.tables}
        self.assertTrue({"_Medidas", "Calendario", "_Documentacao", "_Cargas"} <= names)
        self.assertTrue(all(m.description for _, m in model.measures))


class TestExampleIsGoverned(unittest.TestCase):
    def test_repository_validates(self) -> None:
        import os
        cwd = Path.cwd()
        os.chdir(REPO)
        try:
            buf = io.StringIO()
            with redirect_stdout(buf), redirect_stderr(buf):
                code = cli.main(["validar"])
        finally:
            os.chdir(cwd)
        self.assertEqual(code, 0, buf.getvalue())


class TestPbitRead(unittest.TestCase):
    def test_extract_without_redaction(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.pbit"
            make_pbit(p)
            ex, analysis = pbit.extract(p, do_redact=False)
            self.assertEqual(len(ex.pages), 1)
            self.assertIn("10.0.0.15", ex.tables[0]["partitions"][0]["expression"])
            self.assertIn("Clientes.Nome", ex.pages[0]["visuals"][0]["fields"])


# a typical synced folder (Desktop + SharePoint library): ~90 characters before the repository even starts
USER_ROOT = r"C:\Users\analista.financeiro\Desktop\Documentos - Minha Empresa\_repositorios\powerbi-workspaces"


class TestLongPaths(Sandbox):
    """Power BI Desktop cannot read 260+ character paths (the reported "caminho muito longo" error)."""

    def test_measure_includes_the_next_visual_desktop_creates(self) -> None:
        self.run_cli("novo", "acme/financeiro/controladoria/dre-gerencial")
        dash = self.tmp / "dashboards/acme/financeiro/controladoria/dre-gerencial"
        longa = caminhos.medir(self.tmp, dash, USER_ROOT)
        self.assertTrue(longa.excede, longa)                       # the analyst's folder: does not open
        self.assertTrue(longa.caminho.endswith("visual.json"))
        self.assertIn(r"\2-power-bi\DreGerencial.Report\definition\pages", longa.caminho)
        curta = caminhos.medir(self.tmp, dash, r"C:\pbw")
        self.assertFalse(curta.excede, curta)                      # same dashboard from C:\pbw: opens
        self.assertEqual(longa.tamanho - curta.tamanho, len(USER_ROOT) - len(r"C:\pbw"))
        self.assertGreater(caminhos.folga(self.tmp, dash), len(r"C:\pbw"))

    def test_long_names_warn_on_new_and_validate(self) -> None:
        spec = ("Empresa de Transportes Rodoviarios Integrados/Planejamento Financeiro Corporativo/"
                "Controladoria e Resultados Gerenciais/Demonstrativo de Resultado do Exercicio Gerencial")
        code, out = self.run_cli("novo", spec)
        self.assertEqual(code, 0, out)
        self.assertIn("pbw abrir", out)
        self.assertIn(caminhos.PASTA_CURTA, out)
        code, out = self.run_cli("validar", "demonstrativo-de-resultado-do-exercicio-gerencial")
        self.assertIn("PBW025", out)
        self.assertEqual(code, 0, out)                             # a warning, never a blocked commit

    def test_short_names_do_not_warn(self) -> None:
        self.run_cli("novo", "Acme/Comercial/Vendas/Painel")
        code, out = self.run_cli("validar", "painel")
        self.assertNotIn("PBW025", out)

    def test_subst_parsing_and_drive_choice(self) -> None:
        saida = "P:\\: => C:\\Users\\x\\repo\r\nW:\\: => \\\\?\\C:\\outro\r\n"
        self.assertEqual(caminhos.parse_subst(saida), {"P": r"C:\Users\x\repo", "W": r"C:\outro"})
        mapped = caminhos.parse_subst(saida)
        if __import__("os").name == "nt":                           # paths compare case-insensitively on Windows
            self.assertEqual(caminhos.escolher_letra(mapped, r"c:\users\x\repo", {"C"}), ("P", True))
        self.assertEqual(caminhos.escolher_letra(mapped, r"C:\Users\x\repo", {"C"}), ("P", True))
        self.assertEqual(caminhos.escolher_letra(mapped, r"C:\novo", {"C", "Q"}), ("R", False))
        self.assertEqual(caminhos.escolher_letra({}, r"C:\novo", set(caminhos.LETRAS)), (None, False))

    def test_open_prints_the_project_path(self) -> None:
        self.run_cli("novo", "Acme/Comercial/Vendas/Painel")
        code, out = self.run_cli("abrir", "painel", "--so-caminho")
        self.assertEqual(code, 0, out)
        self.assertIn("Painel.pbip", out)

    def test_open_without_name_lists_dashboards(self) -> None:
        self.run_cli("novo", "Acme/Comercial/Vendas/Painel")
        code, out = self.run_cli("abrir", "--so-caminho")
        self.assertEqual(code, 1)
        self.assertIn("Dashboards: painel", out)

    @unittest.skipUnless(sys.platform == "win32", "subst só existe no Windows")
    def test_short_drive_points_to_the_same_files(self) -> None:
        drive = caminhos.unidade_curta(self.tmp)
        self.assertIsNotNone(drive, "subst não criou a unidade")
        try:
            self.assertTrue((Path(drive + "\\") / "workspaces.toml").exists())
            self.assertEqual(caminhos.unidade_curta(self.tmp), drive)        # reused, not a second drive
        finally:
            caminhos.remover_unidade(drive)


class TestReportChecks(Sandbox):
    def _page(self, dash: Path, title: str) -> Path:
        for pj in dash.glob("2-power-bi/*.Report/definition/pages/*/page.json"):
            if json.loads(pj.read_text(encoding="utf-8"))["displayName"] == title:
                return pj
        raise AssertionError(title)

    def test_broken_field_and_mismatched_names(self) -> None:
        self.run_cli("novo", "Acme/Comercial/Vendas/Painel")
        dash = self.tmp / "dashboards/acme/comercial/vendas/painel"
        code, out = self.run_cli("validar", "painel")
        self.assertNotIn("PBW026", out)
        self.assertNotIn("PBW027", out)
        docs = self._page(dash, "Documentação")
        table = next(v for v in docs.parent.glob("visuals/*/visual.json") if '"Property": "Medida"' in v.read_text(encoding="utf-8"))
        table.write_text(table.read_text(encoding="utf-8").replace('"Property": "Medida"', '"Property": "Medida Antiga"'),
                         encoding="utf-8")
        data = json.loads(table.read_text(encoding="utf-8"))
        data["name"] = "outro"
        table.write_text(json.dumps(data), encoding="utf-8")
        overview = self._page(dash, "Visão Geral")
        page = json.loads(overview.read_text(encoding="utf-8"))
        page["displayName"] = "Documentação"
        overview.write_text(json.dumps(page), encoding="utf-8")
        code, out = self.run_cli("validar", "painel")
        self.assertIn("PBW027", out)
        self.assertIn("_Documentacao[Medida Antiga]", out)
        self.assertIn("visual com name 'outro'", out)
        self.assertIn("duas páginas com o mesmo nome", out)


class TestRepositoryHygiene(unittest.TestCase):
    def _ignored(self, path: str) -> bool:
        import subprocess
        return subprocess.run(["git", "check-ignore", "-q", "--no-index", path], cwd=REPO).returncode == 0

    @unittest.skipUnless(shutil.which("git") and (REPO / ".git").exists(), "precisa do Git")
    def test_gitignore_follows_the_layout(self) -> None:
        base = f"dashboards/acme/financeiro/contas-a-receber/aging-de-titulos/{layout.LEGACY}"
        self.assertTrue(self._ignored(f"{base}/original.pbit"))        # legacy may hold hosts in M
        self.assertTrue(self._ignored(f"{base}/original.pbix"))
        self.assertFalse(self._ignored(f"{base}/extracao/summary.md"))  # the audit trail is versioned
        self.assertFalse(self._ignored("powerbi-graph/GRAPH_REPORT.md"))  # the skill decides (its own .gitignore)

    def test_gitattributes_and_editor_paths_exist_in_the_layout(self) -> None:
        attrs = (REPO / ".gitattributes").read_text(encoding="utf-8")
        for stale in ("analytics/", "docs/dicionario", "legacy/extraction"):
            self.assertNotIn(stale, attrs)
        self.assertIn(f"**/{layout.WORK}/dicionario.md", attrs)
        self.assertNotIn("documentos/legado", (REPO / ".vscode/settings.json").read_text(encoding="utf-8"))

    def test_catalog_does_not_change_by_itself(self) -> None:
        # CI regenerates the catalog and fails on any diff: it must not carry today's date
        import datetime as dt
        text = (REPO / "dashboards/CATALOGO.md").read_text(encoding="utf-8")
        self.assertNotIn(dt.date.today().isoformat(), text)
        self.assertNotIn("Atualizado em", text)

    def test_license_renders_as_markdown(self) -> None:
        text = (REPO / "LICENSE.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# MIT License\n"))
        self.assertIn("THE SOFTWARE IS PROVIDED \"AS IS\"", text)
        self.assertFalse((REPO / "LICENSE").exists())

    @unittest.skipUnless(shutil.which("sh") and sys.platform != "win32", "precisa de sh (fora do Windows)")
    def test_pre_commit_hook_is_valid_shell(self) -> None:
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            hook = Path(d) / "pre-commit"
            hook.write_text(cli.HOOK, encoding="utf-8", newline="\n")
            self.assertEqual(subprocess.run(["sh", "-n", str(hook)]).returncode, 0)
        self.assertIn('-c "import sys; sys.exit(sys.version_info < (3, 11))"', cli.HOOK)


class TestSkill(Sandbox):
    def _install(self, base: Path, version: str) -> Path:
        pasta = base / skill_mod.NOME
        (pasta / "scripts").mkdir(parents=True)
        (pasta / "SKILL.md").write_text(f"---\nname: powerbi-architect\nmetadata:\n  version: \"{version}\"\n---\n",
                                        encoding="utf-8")
        (pasta / "scripts" / "audit_pbip.py").write_text(       # leaves a mark next to the folder it audited
            "import sys\nfrom pathlib import Path\nPath(sys.argv[1] + '.auditado').write_text('ok')\n",
            encoding="utf-8")
        return pasta

    def test_finds_project_and_global_installs(self) -> None:
        home = self.tmp / "home"
        self._install(self.tmp / ".claude/skills", "1.2.0")
        self._install(home / ".codex/skills", "1.1.0")
        found = skill_mod.instalacoes(self.tmp, home)
        self.assertEqual([(i.escopo, i.versao) for i in found], [("projeto", "1.2.0"), ("global", "1.1.0")])
        self.assertEqual(skill_mod.script(self.tmp, "audit_pbip.py", home).parent.parent, found[0].pasta)
        self.assertIsNone(skill_mod.script(self.tmp, "preview_pbir.py", home))

    def test_commands_without_the_skill_explain_how_to_install(self) -> None:
        import os
        old = os.environ.get("HOME"), os.environ.get("USERPROFILE")
        os.environ["HOME"] = os.environ["USERPROFILE"] = str(self.tmp / "sem-skill")
        try:
            self.run_cli("novo", "Acme/Comercial/Vendas/Painel")
            code, out = self.run_cli("skill")
            self.assertEqual(code, 0)
            self.assertIn("/plugin install powerbi-architect", out)
            code, out = self.run_cli("auditar", "painel")
            self.assertEqual(code, 1)
            self.assertIn("install.ps1", out)
        finally:
            for key, value in zip(("HOME", "USERPROFILE"), old):
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_audit_runs_the_skill_script(self) -> None:
        self._install(self.tmp / ".claude/skills", "1.2.0")
        self.run_cli("novo", "Acme/Comercial/Vendas/Painel")
        code, out = self.run_cli("auditar", "painel")
        self.assertEqual(code, 0, out)
        self.assertTrue((self.tmp / "dashboards/acme/comercial/vendas/painel/2-power-bi.auditado").exists())


if __name__ == "__main__":
    unittest.main()
