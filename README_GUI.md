# 🎰 Brazilian Roulette Assistant - Interface Gráfica

Sistema profissional de análise e assistência para apostas em roleta com interface visual moderna.

## 🚀 Como Executar

### 1. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 2. Iniciar o Servidor

```bash
python app.py
```

### 3. Acessar a Aplicação

Abra seu navegador e acesse:
- `http://localhost:5000`
- ou `http://127.0.0.1:5000`

## 📱 Como Usar

### Passo 1: Configuração Inicial
1. Digite o valor da sua banca inicial (ex: 100.00)
2. Selecione as estratégias que deseja ativar:
   - **Cor**: Baseado em sequências de vermelho/preto
   - **Par/Ímpar**: Baseado em sequências de números pares/ímpares
   - **Alto/Baixo**: Baseado em números altos (19-36) ou baixos (1-18)
   - **Dúzias**: Baseado nas três dúzias (1-12, 13-24, 25-36)
   - **Colunas**: Baseado nas três colunas da mesa
   - **Números Frios**: Baseado em números que não saem há muito tempo
3. Clique em "Continuar"

### Passo 2: Aquecimento do Sistema
1. Insira os últimos 12 resultados da roleta
2. Digite do mais recente para o mais antigo
3. Pressione Enter ou clique em "Adicionar" após cada número
4. Quando completar os 12 números, clique em "Iniciar Sistema"

### Passo 3: Uso Durante o Jogo
1. Digite cada novo número que sair na roleta
2. Pressione Enter ou clique em "Processar"
3. O sistema mostrará:
   - **Ação Recomendada**: Onde e quanto apostar
   - **Sinais Ativos**: Apostas em andamento
   - **Histórico**: Últimos 20 números
   - **Números Quentes/Frios**: Análise de frequência
   - **Estatísticas**: Banca atual, lucro/perda, total de giros

## 🎨 Características da Interface

- ✨ Design moderno e elegante com tema de cassino
- 📱 Totalmente responsivo (funciona em desktop, tablet e celular)
- 🎯 Interface intuitiva e fácil de usar
- 💰 Acompanhamento em tempo real da banca
- 📊 Estatísticas visuais detalhadas
- 🔥 Análise de números quentes e frios
- ⚡ Indicadores visuais de sinais ativos
- 🎲 Histórico visual com cores (vermelho/preto/verde)

## 🛠️ Tecnologias Utilizadas

- **Backend**: Flask (Python)
- **Frontend**: HTML5, CSS3, JavaScript
- **Design**: UI/UX moderno com glassmorphism e animações
- **Fontes**: Poppins, Orbitron

## 📊 Estratégias Implementadas

1. **Sistema Martingale**: Progressão de apostas após perdas
2. **Regra La Partage**: Recuperação de 50% em apostas 1:1 quando sai zero
3. **Análise de Sequências**: Detecção de padrões em cores, paridade, etc.
4. **Análise de Atraso**: Detecção de dúzias/colunas atrasadas
5. **Números Frios**: Apostas em números com maior atraso
6. **Limite de Perdas**: Proteção automática após perdas consecutivas

## ⚠️ Importante

- Este é um sistema de assistência e análise estatística
- Não garante lucros e deve ser usado com responsabilidade
- Defina limites de banca e respeite-os
- O jogo pode causar dependência - jogue com moderação

## 🔒 Privacidade

- Todos os dados são processados localmente
- Nenhuma informação é enviada para servidores externos
- Sua sessão é privada e segura

## 📝 Licença

MIT License - Uso educacional e responsável

---

Desenvolvido com ❤️ para proporcionar a melhor experiência de análise de roleta
