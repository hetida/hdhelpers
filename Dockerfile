ARG hd_version=latest
FROM hetida/designer-backend:$hd_version

USER root

RUN pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple --no-deps hdhelpers

USER hd_app

CMD ["bash", "/app/start.sh"]
