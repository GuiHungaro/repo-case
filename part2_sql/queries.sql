-- 1. custo por lead e custo por venda por campanha, do melhor para o pior
WITH gasto_por_campanha AS (
    SELECT campanha_id, ROUND(SUM(gasto), 2) AS gasto_total
    FROM investimento_midia
    GROUP BY campanha_id
),
leads_por_campanha AS (
    SELECT campanha_id, COUNT(*) AS leads
    FROM leads
    WHERE campanha_id IS NOT NULL
    GROUP BY campanha_id
),
vendas_por_campanha AS (
    SELECT l.campanha_id, COUNT(*) AS vendas
    FROM vendas v
    JOIN leads l ON l.lead_id = v.lead_id
    WHERE l.campanha_id IS NOT NULL
    GROUP BY l.campanha_id
)
SELECT
    g.campanha_id,
    g.gasto_total,
    lc.leads,
    CASE WHEN g.gasto_total > 0 AND lc.leads > 0
        THEN ROUND(g.gasto_total / lc.leads, 2) END AS custo_por_lead,
    vc.vendas,
    CASE WHEN g.gasto_total > 0 AND vc.vendas > 0
        THEN ROUND(g.gasto_total / vc.vendas, 2) END AS custo_por_venda
FROM gasto_por_campanha g
LEFT JOIN leads_por_campanha lc ON lc.campanha_id = g.campanha_id
LEFT JOIN vendas_por_campanha vc ON vc.campanha_id = g.campanha_id
ORDER BY custo_por_venda IS NULL, custo_por_venda;

-- 2. funil por campanha: leads que chegaram a cada etapa e perda entre etapas
WITH funil AS (
    SELECT
        COALESCE(campanha_id, '(sem campanha)') AS campanha,
        COUNT(*) AS chegou_novo,
        SUM(CASE WHEN etapa_atual IN ('em_atendimento', 'qualificado', 'briefing_realizado', 'proposta', 'vendido')
            THEN 1 ELSE 0 END) AS chegou_em_atendimento,
        SUM(CASE WHEN etapa_atual IN ('qualificado', 'briefing_realizado', 'proposta', 'vendido')
            THEN 1 ELSE 0 END) AS chegou_qualificado,
        SUM(CASE WHEN etapa_atual IN ('briefing_realizado', 'proposta', 'vendido')
            THEN 1 ELSE 0 END) AS chegou_briefing,
        SUM(CASE WHEN etapa_atual IN ('proposta', 'vendido')
            THEN 1 ELSE 0 END) AS chegou_proposta,
        SUM(CASE WHEN etapa_atual = 'vendido' THEN 1 ELSE 0 END) AS chegou_vendido
    FROM leads
    GROUP BY COALESCE(campanha_id, '(sem campanha)')
)
SELECT
    campanha,
    chegou_novo AS leads,
    chegou_em_atendimento,
    chegou_qualificado,
    chegou_briefing,
    chegou_proposta,
    chegou_vendido,
    ROUND((chegou_novo - chegou_em_atendimento) * 100.0 / chegou_novo, 1) AS perda_novo_atendimento,
    ROUND((chegou_em_atendimento - chegou_qualificado) * 100.0 / chegou_em_atendimento, 1) AS perda_atendimento_qualificado,
    ROUND((chegou_qualificado - chegou_briefing) * 100.0 / chegou_qualificado, 1) AS perda_qualificado_briefing,
    ROUND((chegou_briefing - chegou_proposta) * 100.0 / chegou_briefing, 1) AS perda_briefing_proposta,
    ROUND((chegou_proposta - chegou_vendido) * 100.0 / chegou_proposta, 1) AS perda_proposta_venda
FROM funil
ORDER BY campanha;

-- 3. ticket medio e receita total por campanha, do maior ticket para o menor
WITH receita_por_campanha AS (
    SELECT l.campanha_id, COUNT(*) AS vendas, ROUND(SUM(v.valor_contrato), 2) AS receita_total
    FROM vendas v
    JOIN leads l ON l.lead_id = v.lead_id
    WHERE l.campanha_id IS NOT NULL
    GROUP BY l.campanha_id
)
SELECT
    campanha_id,
    vendas,
    receita_total,
    ROUND(receita_total / vendas, 2) AS ticket_medio
FROM receita_por_campanha
ORDER BY ticket_medio DESC;

-- 4. maior contrato individual e a campanha que o trouxe
SELECT l.campanha_id, v.venda_id, v.lead_id, v.valor_contrato
FROM vendas v
JOIN leads l ON l.lead_id = v.lead_id
ORDER BY v.valor_contrato DESC
LIMIT 1;