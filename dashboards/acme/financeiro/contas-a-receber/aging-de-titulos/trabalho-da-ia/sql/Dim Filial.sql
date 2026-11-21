-- @table: Dim Filial
-- @description: Filiais e regionais da Acme Logística.
-- @grain: 1 linha por filial
SELECT
    f.id_filial AS id_filial,
    f.nome      AS [Filial],
    f.regional  AS [Regional]
FROM bi.vw_filiais AS f
