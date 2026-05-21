from enum import Enum

class ResponseSignal(Enum):

    File_Validated_Succes = "File validated succesfully"
    File_Types_Not_Allowed = "File type not allowed"
    File_Size_Exceeded = "File size too large"
    File_Uploaded_Succesfully = "File uploaded successfully"
    File_Uploaded_Failed = "File uploaded failed"
    PROCESSING_SUCCES = "processing_succes"
    PROCESSING_FAILED = "processing_failed"
    RESPONSE_SIGNAL_ERROR = "no_file_found"
    FILE_ID_ERROR = "no file found with this id"
    PROJECT_NOT_FOUND_ERROR = "project not found"
    INSERTED_INTO_VECTORDB_ERROR = "inserted_into_vectordb_error"
    INSERTED_INTO_VECTORDB_SUCESS = "inserted_into_vectordb_sucess"
    VECTORDB_COLLECTION_RETRIEVED = "vectordb_collection_retrieved"
    VECTORDB_SEARCH_SUCCESS = "vectordb_search_succes"
    VECTORDB_SEARCH_ERROR = "vectordb_search_error"
    RAG_ANSWER_ERROR = "rag_answer_error"
    RAG_ANSWER_SUCCESS = "rag_answer_success"