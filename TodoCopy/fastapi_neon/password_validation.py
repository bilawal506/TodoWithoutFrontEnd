from fastapi import HTTPException


def password_check(passwd:str):
     
    SpecialSym =['#', '%','!',"^",'*','=','+',':',";",'"',"'",'\ ','|','{','/','}','[',']']
    val = True
     
    if len(passwd) < 8:
        raise HTTPException(status_code=400,detail='length should be at least 8')
        val = False
         
    if len(passwd) > 16:
        raise HTTPException(status_code=400,detail='length should be not be greater than 16')
        val = False
         
    if not any(char.isdigit() for char in passwd):
        raise HTTPException(status_code=400,detail='Password should have at least one numeral')
        val = False
         
    if not any(char.isupper() for char in passwd):
        raise HTTPException(status_code=400,detail='Password should have at least one uppercase letter')
        val = False
         
    if not any(char.islower() for char in passwd):
        raise HTTPException(status_code=400,detail='Password should have at least one lowercase letter')
        val = False
         
    if any(char in SpecialSym for char in passwd):
        raise HTTPException(status_code=400,detail="Password can't have any Special Symbols except: $, -, _, @, (, ), &")
        val = False
    if val:
        return val