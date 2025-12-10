# 🗺️ ManaTools 2025: Roadmap Estratégico & Engenharia

**Visão:** Evoluir de "Automação de Modelagem" para "Gestão de Obra Digital (BIM 5D)".
**Responsável:** Lucas Rossetti (Sócio-Diretor / Dev)
**Status:** Em Desenvolvimento Ativo

---

## 🎯 Prioridades de Desenvolvimento (Backlog)

Classificação baseada no ROI (Retorno sobre Investimento de Tempo) para a Maná Engenharia.

| Fase | Módulo | Descrição Técnica | Impacto (Valor) | Esforço (Dev) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1.0** | **Acabamentos** | *Modelagem Fina (LOD 400)* | ⭐⭐⭐⭐⭐ | 🟢 Baixo | ✅ Concluído |
| **1.1** | **Transições** | *Soleiras e Peitoris (Floors)* | ⭐⭐⭐⭐⭐ | 🟡 Médio | 🚀 Próximo |
| **1.2** | **Pintura** | *Mapeamento de Áreas (Spatial Calc)* | ⭐⭐⭐⭐ | 🔴 Alto | ⏳ Pendente |
| **2.0** | **Doc. Auto** | *Vistas Internas (View Gen)* | ⭐⭐⭐ | 🟡 Médio | ⏳ Pendente |
| **2.1** | **Cotas** | *Dimensionamento Auto (References)* | ⭐⭐ | 🔴 Alto | ⏳ Pendente |
| **3.0** | **Custos** | *Linker SINAPI (Data Mining)* | ⭐⭐⭐⭐⭐ | 🔴 Alto | 🔮 Futuro |

---

## 🧱 Fase 1: Fechamento de Modelagem (LOD 400)

O objetivo é garantir que a geometria 3D suporte a extração de quantitativos precisa, sem "chutes".

### ✅ 1.0 - Acabamentos Básicos (Concluído)
- [x] **Criar Piso:** Lajes de acabamento com união booleana.
- [x] **Criar Forro:** Gesso + Tabica (Line Based) com lógica de *flip*.
- [x] **Criar Rodapé:** Wall Sweeps com corte automático em portas (V4).

### 🚀 1.1 - Soleiras e Peitoris (Próximo Passo)
Elemento crítico para o orçamento (Granito vs. Cerâmica).
* **Lógica:** Detectar portas/janelas -> Extrair largura do batente -> Criar `Floor` ou `DirectShape` no vão.
* **Requisito BIM:** Deve descontar a área do piso do ambiente adjacente se houver sobreposição.

### ⏳ 1.2 - Mapeador de Pintura
Evitar a modelagem pesada de "paredes cebola" para pintura.
* **Lógica:** Ler área líquida da parede -> Subtrair rodapés/forros -> Armazenar valor em parâmetro.

---

## 📄 Fase 2: Documentação Automática (Ganho de Tempo)

Foco em reduzir o tempo braçal de detalhamento de interiores.

### ⏳ 2.0 - Gerador de Vistas Internas
* **Feature:** Seleciona Sala -> Gera 4 Elevações -> Aplica Template -> Renomeia (`Q01-Elev-A`).
* **Meta:** Reduzir a criação de vistas de 10 min para 5 segundos por ambiente.

### ⏳ 2.1 - Cotagem Automática
* **Feature:** Lançar *DimensionLines* pegando faces de parede e eixos de esquadrias.
* **Des