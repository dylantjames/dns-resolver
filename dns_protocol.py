"""DNS protocol message format implementation.

Simplified DNS protocol using pipe-delimited encoding.

Wire format:
    QUERY:    QUERY|<query_id>|<domain_name>
    RESPONSE: RESPONSE|<query_id>|<domain_name>|<result_type>|<result_value>
"""


class DNSMessage:
    """DNS protocol message for queries and responses.

    Attributes:
        msg_type: "QUERY" or "RESPONSE".
        query_id: Unique identifier for matching queries to responses.
        domain: Fully qualified domain name.
        result_type: "IP", "NS", or "ERROR" for responses, None for queries.
        result_value: Result data for responses, None for queries.
    """

    def __init__(self, msg_type, query_id, domain, result_type=None, result_value=None):
        self.msg_type = msg_type
        self.query_id = query_id
        self.domain = domain
        self.result_type = result_type
        self.result_value = result_value

    def serialize(self):
        """Convert message to wire format bytes.

        Returns:
            Pipe-delimited UTF-8 encoded bytes.

        Raises:
            ValueError: If msg_type is invalid.
        """
        if self.msg_type == "QUERY":
            return f"QUERY|{self.query_id}|{self.domain}".encode('utf-8')
        elif self.msg_type == "RESPONSE":
            return f"RESPONSE|{self.query_id}|{self.domain}|{self.result_type}|{self.result_value}".encode('utf-8')
        else:
            raise ValueError(f"Unknown message type: {self.msg_type}")

    @staticmethod
    def deserialize(data):
        """Parse wire format bytes into DNSMessage.

        Args:
            data: Raw bytes from network socket.

        Returns:
            Parsed DNSMessage object.
        """
        parts = data.decode('utf-8').split('|')

        if parts[0] == "QUERY":
            return DNSMessage(
                msg_type="QUERY",
                query_id=int(parts[1]),
                domain=parts[2]
            )
        elif parts[0] == "RESPONSE":
            return DNSMessage(
                msg_type="RESPONSE",
                query_id=int(parts[1]),
                domain=parts[2],
                result_type=parts[3],
                result_value=parts[4]
            )
        else:
            raise ValueError(f"Unknown message type: {parts[0]}")

    def __str__(self):
        if self.msg_type == "QUERY":
            return f"QUERY(id={self.query_id}, domain={self.domain})"
        else:
            return f"RESPONSE(id={self.query_id}, domain={self.domain}, {self.result_type}={self.result_value})"
