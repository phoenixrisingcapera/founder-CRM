from pydantic import BaseModel


class SignUpRequest(BaseModel):
    full_name: str
    email: str
    password: str


class SignInRequest(BaseModel):
    email: str
    password: str


class SessionUserResponse(BaseModel):
    id: str
    email: str
    full_name: str


class SessionWorkspaceResponse(BaseModel):
    id: str
    name: str
    slug: str
    active_raise_name: str | None = None
    active_project_id: str | None = None
    active_project_title: str | None = None
    active_goal_type: str | None = None


class SessionResponse(BaseModel):
    user: SessionUserResponse
    workspace: SessionWorkspaceResponse
