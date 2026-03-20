import asyncio

import nxd.data_product.context as ctx
from langchain_core.prompts.prompt import PromptTemplate
from langchain_core.tools.retriever import create_retriever_tool

# from langchain.chains.combine_documents import create_stuff_documents_chain
# from langchain.chains.retrieval import create_retrieval_chain
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langchain_pinecone import PineconeEmbeddings
from langchain_pinecone import PineconeVectorStore
from langgraph.prebuilt import create_react_agent
from nxd.data_product.client import create_client

nxd_client = create_client(hostname="dp.demo.trynxd.com")
au_competitor_analysis_data_product = nxd_client.data_product(
    data_product="au-competitor-analysis-demo"
)
au_competitor_analysis_output = au_competitor_analysis_data_product.get_outputs(
    "pinecone", ctx.PineconeOutput
)

public_disclosures_data_product = nxd_client.data_product(
    data_product="public-disclosures-demo"
)
public_disclosures_output = public_disclosures_data_product.get_outputs(
    "pinecone", ctx.PineconeOutput
)

embeddings = PineconeEmbeddings(
    model="llama-text-embed-v2",
    api_key=au_competitor_analysis_output.password,  # type: ignore
)

au_competitor_analysis_retriever = PineconeVectorStore(
    index_name="finance-documents-pilot",
    # index_name=au_competitor_analysis_output.index,
    embedding=embeddings,
    namespace=au_competitor_analysis_output.namespace,
    pinecone_api_key=au_competitor_analysis_output.password,
).as_retriever(
    search_kwargs={
        "namespace": "au-competitor-analysis-documents",
        "k": 500,  # just a whole lot of documents
    },
)

public_disclosures_retriever = PineconeVectorStore(
    index_name="finance-documents-pilot",
    # index_name=public_disclosures_output.index,
    embedding=embeddings,
    namespace=public_disclosures_output.namespace,
    pinecone_api_key=public_disclosures_output.password,
).as_retriever(
    search_kwargs={
        "namespace": "public-disclosures-disclosures",
        "k": 10,
        "fetch_k": 20,
    },
)

llm = ChatOpenAI(
    openai_api_key="",  # type: ignore
    model="gpt-4o-mini",
    temperature=0.0,
)

data_product_mcps = MultiServerMCPClient(
    {
        "product-competitiveness": {
            "url": "https://dp.demo.trynxd.com/product-competitiveness-demo/rpcs/mcp-api/mcp/",
            "transport": "streamable_http",
            "headers": {
                "x-nextdata-token": "",  # TODO nxd token
            },
        },
    }
)

au_competitor_analysis_retriever_tool = create_retriever_tool(
    au_competitor_analysis_retriever,
    name="documents",
    description="Announcement documents from NASDAQ listed companies",
    response_format="content_and_artifact",  # ensure document metadata is also returned
    document_prompt=PromptTemplate.from_template(
        "page_content: {page_content} "
        "title: {headline} "
        "companies: {companies} "
        "date: {date} "
        "symbol: {symbol}"
        "document_key: {document_key} "
        "annoucement_types: {annoucement_types} "
    ),
)
public_disclosures_retriever_tool = create_retriever_tool(
    public_disclosures_retriever,
    name="disclosures",
    description="APS 330 Public Disclosures from NASDAQ listed companies",
    document_prompt=PromptTemplate.from_template(
        "page_content: {page_content} filename: {filename} url: {url} "
    ),
)


async def chatbot():
    # basic retrievel
    # combine_docs_chain = create_stuff_documents_chain(llm, retrieval_qa_chat_prompt)
    # retrieval_chain = create_retrieval_chain(retriever, combine_docs_chain)

    # # with context from Pinecone
    # response = retrieval_chain.invoke(
    #     {"input": "Provide a summary of Westpac's 3Q25 update"},
    # )

    # combined tooling agent
    tools = [
        # *await data_product_mcps.get_tools(),
        au_competitor_analysis_retriever_tool,
        # public_disclosures_retriever_tool,
    ]

    agent = create_react_agent(
        llm,
        tools,
    )

    # content = "What are some recent term deposit rates provided by Westpac?"
    # content = "Provide income insights from WBC 3Q25 Update"
    # content = "What type of information does the document Westpac 1H23 Presentation and Investor Discussion Pack hold?"
    content = "Provide some insights on the document Westpac 1H23 Presentation and Investor Discussion Pack"
    # content = "Provide a list of recent Westpac annoucements"
    # content = "Can you provide a summary of of the document WBC 3Q24 Investor Discussion Pack?"
    r = await agent.ainvoke({"messages": [{"role": "user", "content": content}]})
    import pprint

    pprint.pprint(r)

    # response
    #   "Here are the key income insights from Westpac's 3Q25 Update for the three months ended June 30, 2025:
    #       1. **Net Profit Contribution**: Westpac reported a net profit contribution of AUD 1,380 million for the financial year ended March 31, 2025, which represents an 11% increase compared to FY24.
    #       2. **Operating Income**: The operating income for the Banking and Financial Services division was AUD 3,237 million, reflecting a 1% increase from the previous year.
    #       3. **Net Interest Margin (NIM)**: The net interest margin for 3Q25 was reported at 2.01%, which is an increase of 13 basis points compared to the average for the first half of FY25.
    #       4. **Total Income**: For the financial year ended March 31, 2025, total income was AUD 10,995 million, up 5% compared to the second half of FY24.
    #       5. **Profit Before Provisions**: The profit before provisions was AUD 5,253 million, marking a 6% increase from the second half of FY24.
    #       6. **Earnings per Share (EPS)**: The earnings per share for the period were reported at 120.1 cents, which is a 13% increase compared to the second half of FY24.
    #       7. **Return on Equity (ROE)**: The return on equity was reported at 10.2%, up 94 basis points from the second half of FY24.
    #       8. **Operating Expenses**: Total operating expenses were AUD 12,140 million for the year ended March 31, 2025, which remained broadly in line with the prior year.
    #
    #   These insights indicate a strong financial performance for Westpac in 3Q25, with notable increases in net profit, operating income, and earnings per share."


if __name__ == "__main__":
    asyncio.run(chatbot())
