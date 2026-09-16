from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List


class BaseResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: Optional[dict] = None


class UserBase(BaseModel):
    username: str = Field(..., max_length=50, description="用户名")


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="密码")
    confirm_password: str = Field(..., min_length=6, description="确认密码")


class RoleBrief(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)


class UserResponse(UserBase):
    id: int
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    roles: List[RoleBrief] = []

    model_config = ConfigDict(from_attributes=True)

class UserUpdateRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=1, max_length=50, description="用户名")
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    avatar: Optional[str] = Field(None, description="头像URL")


class UserLogin(BaseModel):
    username: str = Field(..., max_length=50, description="用户名")
    password: str = Field(..., min_length=6, description="密码")


class TokenData(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LoginResponse(BaseModel):
    user: UserResponse
    token: TokenData


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class UserRoleUpdate(BaseModel):
    role_ids: List[int] = Field(..., description="角色ID列表")

class PasswordUpdateRequest(BaseModel):
    old_password: str
    new_password: str