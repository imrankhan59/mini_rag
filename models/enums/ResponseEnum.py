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