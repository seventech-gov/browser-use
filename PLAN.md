# Sumário {#sumário}

[Sumário](#sumário)

[Rascunho Conceito](#rascunho-conceito)  
Refs:

- [https://www.browse.ai/website-to-api](https://www.browse.ai/website-to-api)  
- [https://axiom.ai/blog/](https://axiom.ai/blog/)  
- [https://automatio.ai/](https://automatio.ai/)

# Rascunho Conceito {#rascunho-conceito}

**O que queremos?**  
	Uma tecnologia capaz de mapear uma série de ações na internet que culminam em um resultado final, seja ele um código de pagamento, uma informação, um resultado com revisão de IA, etc.

**Como fazer isso?**  
	Precisaremos dividir em quatro frentes diferentes.  
O **mapper**: responsável por entender os campos, os passos, os botões, as ações. Ou seja, ele roteia o caminho para chegar em um sucesso para determinada ação.  
O **planner**: ele pega a saída do mapper e transforma em um plano executável.  
O **executor**: ele pega o plano gerado e executa de maneira rápida, eficiente e gera uma saída satisfatória de acordo com o plano.  
O **barramento de API**: aqui os planos são registrados e segue o padrão ouro de APIs, onde com o ID do plano \+ parâmetros, conseguimos executar. 

**Condições para cada frente e roadmap:**

* Mapper  
  * Essa etapa pode ter duas formas de acontecer, semi-guiada, ou seja, o usuário insere um objetivo e nosso sistema dá conta de encontrar a saída perfeita e pode ou não precisar da ajuda do usuário para enfrentar determinadas fases do mapping.  
  * Ou forma (mais adequada para desenvolver nesse primeiro momento) seria termos uma extensão no navegador capaz de fazer um “recording” das ações do usuário, mapeando os inputs, campos, steps e submissões e ao mesmo tempo o usuário ser capaz de “marcar” ou determinar o que seria o resultado daquela ação.  
  * Nesses dois caminhos, a saída do mapa precisa ser a mesma, para que o planner consiga gerar o plano de execução.  
  * **Stack sugerida:**  
    * Python  
    * Lang Graph (futuramente)  
    * Browser Use (futuramente)  
    * Javascript/Typescript (extensão)  
    * Sugestões???  
* Planner  
  * Pode ou não estar incorporado no mapper, a ideia é que fosse uma etapa segregada, assim nós mantemos responsabilidades divididas e mitigarmos possíveis gargalos e “bagunças” no código.  
  * **Stack sugerida:**  
    * ??  
* Executor  
  * Aqui o negócio precisa ser rápido, eficiente, leve e escalável, em tese será a etapa mais demandada e que terá o I/O maior.  
  * Basicamente ele pega o plano gerado \+ os params recebidos do barramento e executa.  
  * **Stack sugerida:**  
    * Go  
    * Chrome CDN  
    * Playwright  
* Barramento de API  
  * Aqui será todo o gerenciamento do sistema, teremos endpoints que no sentido literal servem a cada uma das frentes, ou seja, ao mapper, planner e executor, sendo esse último, responsável por receber o ID de um plano, os parâmetros e trazer resultados.

# 

# Estrutura de dados padrão entres frentes

# Objetivo

[browser-use.md](https://gist.github.com/fredzolio/919cdb14946f2e75309f32ce58b491b9#file-browser-use-md)

Dev interface

- run a objective  
- search objectives  
- create/search one/many objectives

Definitions:

- UI graph (what the user/AI does)  
- Execution graph  
  - Requests  
  - UI graph playwright

**Functions**

- create/search one/many objectives  
  - input:  
    - prompt with intention  
  - backend:  
    - search if similar objects exists  
    - create the UI graph   
    - create/test the execution graph from UI graph  
    - create/save metadata of objective  
    - create API endpoint  
  - output:  
    - objective endpoint  
- run a objective  
  - input:  
    - activate API endpoint  
  - backend:  
    - execute execution graph  
  - output:  
    - set of artifacts   
    - success message  
- search objectives  
  - input:  
    - prompt with intention  
  - backend:  
    - search similar objectives  
  - output:  
    - ordered objective endpoint list

**Objects**

**objective**

- Something boring people wants to automate  
- UI graph  
  - Set of ordered **steps**  
  - Set of ordered **states**  
- Execution graph  
- Can return an **artifact**  
- An **objective** can be a set of ordered **objectives: list of objectives with a sequence\_id**  
- Parameters:  
  - objective\_id  
  - description  
  - Metadata about it  
  - All data that the user has to input to achieve objective  
  - All data that has to be fetched in runtime that user has to fill  
  - **set of ordered steps**  
- Return:  
  - Success/fail  
  - set of **artifacts**  
- Examples:  
  - Pay a bill  
  - Get a seat on the cinema  
  - Get latest news from top 5 websites  
  - Buy pet food at the PetLove website  
  - Add a new HSM to wetalkie software  
  - Get latest papers from up-to-date  
  - Schedule a doctor's appointment  
  - Upload medical bill to three different system

**artifact**

- Is relevant for the user  
- Is a data file  
- Can be a pointer for a data file sent by email/message/etc…  
- An artifact is a file or collection of files produced during an objective run. Artifacts allow you to persist data after a job has completed, and share that data with another job in the same workflow. Or share the data with the user.  
- Examples  
  - base64 PDF/image  
  - string (pix, bar-code...)  
  - email  
  - message  
  - auth cookie   
  - .txt, .pdf, .jpeg, .xxx

**UI Graph**  
**step**

- An action in a browser  
- Click or keyboard input → requests  
- Change of **state**  
- Parameters:  
  - sequence\_id  
  - type of input (click, keyboard)  
  - params of input  
    - if click, position, xpath, etc…  
    - if keyboard, payload  
  - http network requisitions  
  - **state**  
- Returns:  
  - None  
- Examples:  
  - Input data  
  - Select data  
  - Navigate to other page  
    - reload  
  - Go through captcha  
  - wget / curl / request  
    - Download **artifact**  
    - Upload

**state**

- all information that are loaded between steps (the payload send to the agent)  
  - dom css  
  - dom tree  
  - nodes  
  - dom\_hash  
- Returns:  
  - all current relevant browser data  
  - all current step options

**Execution Graph**  
**…**  
