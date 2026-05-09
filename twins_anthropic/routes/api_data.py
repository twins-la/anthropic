"""Catch-all for unknown ``/v1/<rest>`` paths under the Anthropic API
prefix.

Closes twins-la/twins-la#2 (anthropic half): without this catch-all,
Flask returns its default HTML 404 on any unimplemented endpoint, which
breaks SDK consumers that decode `Content-Type: application/json`. The
canonical Anthropic envelope is ``{type: "error", error: {type:
"not_found_error", message: ...}}``.
"""

from flask import Blueprint, request

from ..errors import anthropic_not_found

api_data_bp = Blueprint("api_data", __name__)


@api_data_bp.route(
    "/v1/<path:rest>",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
def unknown_v1_path(rest: str):
    return anthropic_not_found(
        f"The API endpoint /v1/{rest} does not exist"
    )
