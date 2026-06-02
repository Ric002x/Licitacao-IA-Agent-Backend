import os
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.service.agentes.agente_rating_score import analise_ia
from dotenv import load_dotenv
from app.schemas.licitacoes import FiltroLicitacao
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from sqlalchemy.orm import Session
from selenium.webdriver.chrome.options import Options
from app.models.models import (
    RpaScrapEvent, RpaScrapResult,
    RpaRequestStepEnum, RpaRequestStatusEnum
)
from selenium.common.exceptions import TimeoutException


# ThreadPoolExecutor para executar tarefas síncronas em background
executor = ThreadPoolExecutor(max_workers=5)


# 1. Setup Chrome Options
options = Options()
options.add_argument("--headless=new")
options.add_argument("--window-size=1920,1080")

# 2. Recommended flags for stability
options.add_argument("--disable-gpu")    # Often needed in Windows environments
# Essential for running in Docker/Linux
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")


load_dotenv()


def get_links(driver: Chrome, filtro: FiltroLicitacao):

    WebDriverWait(driver, 10).until(EC.presence_of_element_located((
        By.XPATH, "//label[contains(@for, 'ufs')]"
    )))

    # inserir palavra chave
    if filtro.palavra_chave:
        palavra_chave_input = driver.find_element(
            By.XPATH, "//input[@id='keyword']"
        )
        palavra_chave_input.send_keys(filtro.palavra_chave)

    # inserir estados
    if filtro.ufs and len(filtro.ufs) > 0:
        driver.find_element(
            By.XPATH, "//pncp-select[.//label[contains(@for, 'ufs')]]//input"
        ).click()

        for i in filtro.ufs:
            option = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, f"//div[contains(@title, '{i}')]")
                )
            )
            option.click()

    # inserir modalidade de contratação
    if filtro.modalidades_de_contratacao and \
            len(filtro.modalidades_de_contratacao) > 0:
        driver.find_element(
            By.XPATH, "//pncp-select[.//label[contains(@for, 'modalidades')]]//input"  # noqa: E501
        ).click()
        for i in filtro.modalidades_de_contratacao:
            option = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, f"//div[contains(@title, '{i}')]")
                )
            )
            option.click()

    # Pesquisar com filtros
    botao_pesquisar = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[.//span[contains(text(), 'Pesquisar')]]")
        )
    )
    driver.execute_script("arguments[0].click();", botao_pesquisar)
    time.sleep(5)

    WebDriverWait(driver, 10).until(EC.presence_of_element_located((
        By.TAG_NAME, "pncp-items-list"
    )))

    links = []
    for i in range(2):
        container = driver.find_element(By.TAG_NAME, "pncp-items-list")
        div_main = container.find_element(By.CLASS_NAME, "br-list")
        itens_list = div_main.find_elements(By.XPATH, "./div")

        for i in itens_list:
            link = i.find_element(By.TAG_NAME, "a").get_attribute("href")
            links.append(link)

        try:
            next_page = driver.find_element(
                By.XPATH, "//button[contains(@aria-label, 'Página seguinte') and not(@disabled)]")  # noqa: E501
            driver.execute_script("arguments[0].click();", next_page)
            time.sleep(1)
        except NoSuchElementException:
            break

    return links


def get_contract_itens(driver: Chrome) -> list | None:
    data_itens = []
    id = 1

    while True:
        MAX_RETRY = 3
        for tentativa in range(MAX_RETRY):
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//pncp-tab[contains(@title, 'Itens')]//datatable-body//datatable-scroller/datatable-row-wrapper"))  # noqa: E501
                )
                break
            except TimeoutException:
                if tentativa == MAX_RETRY - 1:
                    return

        data_table = driver.find_elements(
            By.XPATH, "//pncp-tab[contains(@title, 'Itens')]//datatable-body//datatable-scroller/datatable-row-wrapper"  # noqa: E501
        )

        for i in data_table:
            item_dict = {}
            item_dict['id'] = id
            try:
                item_dict['descricao'] = i.find_element(
                    By.XPATH, ".//div[contains(@class, 'datatable-row-center')]/datatable-body-cell[2]//span"  # noqa: E501
                ).text
                item_dict['quantidade'] = i.find_element(
                    By.XPATH, ".//div[contains(@class, 'datatable-row-center')]/datatable-body-cell[3]//span"  # noqa: E501
                ).text
                item_dict['valor_unitario_estimado'] = i.find_element(
                    By.XPATH, ".//div[contains(@class, 'datatable-row-center')]/datatable-body-cell[4]//span"  # noqa: E501
                ).text
                item_dict['valor_total_estimado'] = i.find_element(
                    By.XPATH, ".//div[contains(@class, 'datatable-row-center')]/datatable-body-cell[5]//span"  # noqa: E501
                ).text
                id = id + 1

                data_itens.append(item_dict)
            except NoSuchElementException:
                pass

        try:
            next_button = driver.find_element(
                By.XPATH, "//pncp-tab[contains(@title, 'Itens')]//button[@id='btn-next-page' and not(@disabled)]")  # noqa: E501
            driver.execute_script("arguments[0].click();", next_button)
            time.sleep(1)

        except NoSuchElementException:
            break

    return data_itens


def get_edital_files_data(driver: Chrome):

    MAX_RETRY = 3
    for tentativa in range(MAX_RETRY):
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((
                By.XPATH, "//pncp-tab-set//ul"
            )))

            break
        except TimeoutException:
            if tentativa == MAX_RETRY - 1:
                return

    arquivos_elemento_button = driver.find_element(
        By.XPATH, "//pncp-tab-set//ul/li[2]/button"
    )
    driver.execute_script("arguments[0].click();", arquivos_elemento_button)
    time.sleep(1)

    files = []
    id = 1

    while True:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//pncp-tab[contains(@title, 'Arquivos')]//datatable-body//datatable-scroller/datatable-row-wrapper"))  # noqa: E501
        )

        data_table = driver.find_elements(
            By.XPATH, "//pncp-tab[contains(@title, 'Arquivos')]//datatable-body//datatable-scroller/datatable-row-wrapper"  # noqa: E501
        )

        for i in data_table:
            item_dict = {}
            item_dict['id'] = id
            try:
                item_dict['file_name'] = i.find_element(
                    By.XPATH, ".//div[contains(@class, 'datatable-row-center')]/datatable-body-cell[1]//span"  # noqa: E501
                ).text
                item_dict['data_hora'] = i.find_element(
                    By.XPATH, ".//div[contains(@class, 'datatable-row-center')]/datatable-body-cell[2]//div"  # noqa: E501
                ).text
                item_dict['tipo'] = i.find_element(
                    By.XPATH, ".//div[contains(@class, 'datatable-row-center')]/datatable-body-cell[3]//span"  # noqa: E501
                ).text
                link = i.find_element(
                    By.XPATH, ".//div[contains(@class, 'datatable-row-center')]/datatable-body-cell[4]//a"  # noqa: E501
                )
                item_dict['link'] = link.get_attribute("href")
                id = id + 1

                files.append(item_dict)
            except NoSuchElementException:
                pass
        try:
            next_button = driver.find_element(
                By.XPATH, "//pncp-tab[contains(@title, 'Arquivos')]//button[@id='btn-next-page' and not(@disabled)]")  # noqa: E501
            driver.execute_script("arguments[0].click();", next_button)
            time.sleep(1)

        except NoSuchElementException:
            break

    return files


def get_descricao_licitacao(link: str, driver: Chrome):
    driver.get(link)

    MAX_RETRY = 3
    for tentativa in range(MAX_RETRY):
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((
                    By.XPATH, "//strong[text()='Local:']/following-sibling::span"  # noqa: E501
                ))
            )

            break
        except TimeoutException:
            if tentativa == MAX_RETRY - 1:
                return

    descricao = {}

    descricao['link'] = link

    descricao['nome'] = driver.find_element(
        By.TAG_NAME, "h1"
    ).text
    descricao['local'] = driver.find_element(
        By.XPATH, "//strong[text()='Local:']/following-sibling::span").text

    descricao['orgao'] = driver.find_element(
        By.XPATH, "//strong[text()='Órgão:']/following-sibling::span").text

    try:
        descricao['unidade_compradora'] = driver.find_element(
            By.XPATH, "//p[.//strong//span[contains(text(), 'Unidade compradora')]]//span[not(ancestor::strong)]").text  # noqa: E501
    except NoSuchElementException:
        descricao['unidade_compradora'] = ""

    descricao['modalidade_de_contratacao'] = driver.find_element(
        By.XPATH, "//strong[text()='Modalidade da contratação:']/following-sibling::span").text  # noqa: E501

    descricao['amparo_legal'] = driver.find_element(
        By.XPATH, "//strong[text()='Amparo legal: ']/following-sibling::span").text  # noqa: E501

    descricao['tipo'] = driver.find_element(
        By.XPATH, "//strong[text()='Tipo:']/following-sibling::span").text

    descricao['modo_de_disputa'] = driver.find_element(
        By.XPATH, "//strong[text()='Modo de disputa:']/following-sibling::span").text  # noqa: E501

    descricao['registro_de_preco'] = driver.find_element(
        By.XPATH, "//strong[text()='Registro de preço: ']/following-sibling::span").text  # noqa: E501

    descricao['fonte_orcamentaria'] = driver.find_element(
        By.XPATH, "//strong[text()='Fonte orçamentária: ']/following-sibling::span").text  # noqa: E501

    descricao['data_divulgacao'] = driver.find_element(
        By.XPATH, "//strong[text()='Data de divulgação no PNCP:']/following-sibling::span").text  # noqa: E501

    descricao['situacao'] = driver.find_element(
        By.XPATH, "//strong[text()='Situação:']/following-sibling::span").text

    descricao['data_inicio_de_recebimento_de_propostas'] = driver.find_element(
        By.XPATH, "//strong[text()='Data de início de recebimento de propostas:']/following-sibling::span").text  # noqa: E501

    descricao['data_fim_de_recebimento_de_propostas'] = driver.find_element(
        By.XPATH, "//strong[text()='Data fim de recebimento de propostas:']/following-sibling::span").text  # noqa: E501

    descricao['id_contratacao_pncp'] = driver.find_element(
        By.XPATH, "//strong[text()='Id contratação PNCP:']/following-sibling::span").text  # noqa: E501

    descricao['fonte'] = driver.find_element(
        By.XPATH, "//strong[text()='Fonte: ']/following-sibling::span").text

    descricao['objeto'] = driver.find_element(
        By.CLASS_NAME, "conteudo-objeto").text

    try:
        descricao['informacao_complementar'] = driver.find_element(
            By.XPATH, "//strong[text()='Informação complementar:']/following-sibling::span").text  # noqa: E501
    except NoSuchElementException:
        descricao['informacao_complementar'] = ""

    descricao['valor_estimado_da_compra'] = driver.find_element(
        By.XPATH, "//strong[text()=' VALOR TOTAL ESTIMADO DA COMPRA ']/following-sibling::span").text  # noqa: E501

    descricao['valor_homologado_da_compra'] = driver.find_element(
        By.XPATH, "//strong[text()=' VALOR TOTAL HOMOLOGADO DA COMPRA ']/following-sibling::span").text  # noqa: E501

    return descricao


def get_licitacoes(driver: Chrome, links: list) -> list[dict]:
    licitacoes = []
    seq = 1

    for link in links:
        try:
            descricao = get_descricao_licitacao(link, driver)
            itens_licitacao = get_contract_itens(driver)
            files = get_edital_files_data(driver)

        except Exception:
            continue

        time.sleep(1)

        licitacoes.append({
            "numero": seq,
            "descricao": descricao,
            "itens": itens_licitacao,
            "files_data": files
        })

        seq = seq + 1

    return licitacoes


def iniciar_rpa(
        db: Session, filtro: FiltroLicitacao, request_id: str
):
    """Função síncrona que executa o RPA (pode ser chamada em thread)"""
    from selenium import webdriver

    try:
        driver = webdriver.Chrome(options)
        link = os.getenv("PNCPLINK", "")
        driver.get(link)

        licit_links = get_links(
            driver,
            filtro
        )

        db.query(RpaScrapEvent).filter(
            RpaScrapEvent.request_id == request_id
        ).update({
            RpaScrapEvent.step: RpaRequestStepEnum.PROCESSING,
            RpaScrapEvent.status: RpaRequestStatusEnum.PROCESSING,
            RpaScrapEvent.message: "Licitacões encontradas"
        })
        db.commit()

        licitacoes = get_licitacoes(
            driver, licit_links
        )

        # Atualizar status de inicio de avaliação da IA
        db.query(RpaScrapEvent).filter(
            RpaScrapEvent.request_id == request_id
        ).update({
            RpaScrapEvent.message: "Iniciando a avaliação da IA para as licitacoes encontradas"  # noqa: E501
        })
        db.commit()

        rpa_items = []
        for licitacao in licitacoes:
            item = RpaScrapResult(
                request_id=request_id,
                payload=licitacao
            )

            rpa_items.append(item)

        db.query(RpaScrapResult).filter(
            RpaScrapResult.request_id == request_id
        ).delete()

        db.add_all(rpa_items)
        db.commit()

        resultados = db.query(
            RpaScrapResult.id, RpaScrapResult.payload).filter(
            RpaScrapResult.request_id == request_id
        ).all()

        analise_ia(db, filtro, resultados)

        db.query(RpaScrapEvent).filter(
            RpaScrapEvent.request_id == request_id
        ).update({
            RpaScrapEvent.step: RpaRequestStepEnum.COMPLETED,
            RpaScrapEvent.status: RpaRequestStatusEnum.SUCCESS,
            RpaScrapEvent.message: f"Processo concluído com {len(licitacoes)} licitações"  # noqa: E501
        })
        db.commit()

    except Exception:
        # Atualizar status de erro
        db.query(RpaScrapEvent).filter(
            RpaScrapEvent.request_id == request_id
        ).update({
            RpaScrapEvent.step: RpaRequestStepEnum.COMPLETED,
            RpaScrapEvent.status: RpaRequestStatusEnum.FAILURE,
            RpaScrapEvent.message: "Erro: não foi possível concluir a buscar, por favor, tente novamente!"  # noqa: E501
        })
        db.commit()
        raise
    finally:
        driver.close()

    return licitacoes


async def iniciar_rpa_background(
        db: Session, filtro: FiltroLicitacao, request_id: str
):
    """Função assíncrona que executa o RPA em background (thread pool)"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        executor,
        iniciar_rpa,
        db,
        filtro,
        request_id
    )
