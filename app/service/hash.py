"""
Serviço de hashing de senhas
Encapsula a lógica de hashing e validação de senhas usando bcrypt
"""
import bcrypt


def hash_password(password: str) -> str:
    """
    Hash uma senha em texto plano usando bcrypt

    Args:
        password: Senha em texto plano

    Returns:
        str: Senha com hash
    """
    salt = bcrypt.gensalt()
    senha_cript = bcrypt.hashpw(password.encode("utf-8"), salt)
    return senha_cript.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica se uma senha em texto plano corresponde ao hash armazenado

    Args:
        plain_password: Senha em texto plano fornecida pelo usuário
        hashed_password: Hash da senha armazenado no banco de dados

    Returns:
        bool: True se a senha é válida, False caso contrário
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
        )
