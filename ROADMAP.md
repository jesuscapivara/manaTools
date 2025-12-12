# 🗺️ ManaTools 2025: Roadmap Estratégico & Engenharia

**Visão:** Evoluir de "Automação de Modelagem" para "Gestão de Obra Digital (BIM 5D)".
**Responsável:** Lucas Rossetti (Sócio-Diretor / Dev)
**Status:** Em Desenvolvimento Ativo

---

## 📊 Resumo do Progresso

**Concluído:**

- ✅ Fase 1.0: Acabamentos Básicos (Piso, Forro, Rodapé, Revestimento)
- ✅ Fase 1.1: Transições e Proteções (Soleiras, Pingadeiras)
- ✅ Fase 1.5: Esquadrias (Smart Renamer, Type Mark)
- ✅ Fase 1.6: Gestão (Login, Exportar PDFs)
- ✅ Fase 1.7: Modificações (Unir Elementos)

**Em Desenvolvimento:**

- ⏳ Fase 1.2: Mapeador de Pintura
- ⏳ Fase 2.0: Gerador de Vistas Internas
- ⏳ Fase 2.1: Cotagem Automática

**Futuro:**

- 🔮 Fase 3.0: Linker SINAPI

---

## 🎯 Prioridades de Desenvolvimento (Backlog)

Classificação baseada no ROI (Retorno sobre Investimento de Tempo) para a Maná Engenharia.

| Fase    | Módulo          | Descrição Técnica                    | Impacto (Valor) | Esforço (Dev) | Status       |
| :------ | :-------------- | :----------------------------------- | :-------------- | :------------ | :----------- |
| **1.0** | **Acabamentos** | _Modelagem Fina (LOD 400)_           | ⭐⭐⭐⭐⭐      | 🟢 Baixo      | ✅ Concluído |
| **1.1** | **Transições**  | _Soleiras e Peitoris (Floors)_       | ⭐⭐⭐⭐⭐      | 🟡 Médio      | ✅ Concluído |
| **1.2** | **Pintura**     | _Mapeamento de Áreas (Spatial Calc)_ | ⭐⭐⭐⭐        | 🔴 Alto       | ⏳ Pendente  |
| **2.0** | **Doc. Auto**   | _Vistas Internas (View Gen)_         | ⭐⭐⭐          | 🟡 Médio      | ⏳ Pendente  |
| **2.1** | **Cotas**       | _Dimensionamento Auto (References)_  | ⭐⭐            | 🔴 Alto       | ⏳ Pendente  |
| **3.0** | **Custos**      | _Linker SINAPI (Data Mining)_        | ⭐⭐⭐⭐⭐      | 🔴 Alto       | 🔮 Futuro    |

---

## 🧱 Fase 1: Fechamento de Modelagem (LOD 400)

O objetivo é garantir que a geometria 3D suporte a extração de quantitativos precisa, sem "chutes".

### ✅ 1.0 - Acabamentos Básicos (Concluído)

- [x] **Criar Piso:** Lajes de acabamento com união booleana.
- [x] **Criar Forro:** Gesso + Tabica (Line Based) com lógica de _flip_.
- [x] **Criar Rodapé:** Wall Sweeps com corte automático em portas (V4).
- [x] **Criar Revestimento:** Aplicação de revestimentos em paredes com controle de altura e offset.

### ✅ 1.1 - Transições e Proteções (Concluído)

- [x] **Criar Soleira:** Criação de soleiras (Floors) sob portas selecionadas. Detecção automática de largura do batente.
- [x] **Criar Pingadeira:** Geração inteligente de pingadeiras em janelas com detecção de face externa.

### ⏳ 1.2 - Mapeador de Pintura

Evitar a modelagem pesada de "paredes cebola" para pintura.

- **Lógica:** Ler área líquida da parede -> Subtrair rodapés/forros -> Armazenar valor em parâmetro.

---

## 🪟 Fase 1.5: Esquadrias (Concluído)

Ferramentas para gestão e organização de portas e janelas.

### ✅ 1.5 - Renomeação e Marcação (Concluído)

- [x] **Smart Renamer:** Renomeação inteligente de tipos de portas e janelas com leitura segura de parâmetros.
- [x] **Type Mark:** Atualização automática de marcas de tipo em esquadrias.

---

## 🔧 Fase 1.6: Gestão e Utilidades (Concluído)

Ferramentas de gestão de projeto e automação de processos.

### ✅ 1.6 - Gestão de Projeto (Concluído)

- [x] **Login:** Sistema de autenticação de usuários com validação de licenças e HWID lock.
- [x] **Exportar PDFs:** Exportação em lote de pranchas com nomenclatura personalizada e bypass de regras do Revit.

---

## 🔨 Fase 1.7: Modificações (Concluído)

Ferramentas para modificação e otimização de elementos.

### ✅ 1.7 - União de Elementos (Concluído)

- [x] **Unir Elementos:** União automática de elementos sobrepostos com interface gráfica.

---

## 📄 Fase 2: Documentação Automática (Ganho de Tempo)

Foco em reduzir o tempo braçal de detalhamento de interiores.

### ⏳ 2.0 - Gerador de Vistas Internas

- **Feature:** Seleciona Sala -> Gera 4 Elevações -> Aplica Template -> Renomeia (`Q01-Elev-A`).
- **Meta:** Reduzir a criação de vistas de 10 min para 5 segundos por ambiente.

### ⏳ 2.1 - Cotagem Automática

- **Feature:** Lançar _DimensionLines_ pegando faces de parede e eixos de esquadrias.
- **Desafio:** Detecção automática de referências de parede e eixos de esquadrias.

---

## 💰 Fase 3: Integração de Custos (Futuro)

### 🔮 3.0 - Linker SINAPI

- **Feature:** Integração com base de dados SINAPI para extração automática de custos.
- **Lógica:** Data mining de composições SINAPI baseado em elementos BIM modelados.
