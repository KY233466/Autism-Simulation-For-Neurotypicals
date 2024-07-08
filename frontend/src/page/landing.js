import { Link, useParams } from "react-router-dom";
import { useState, useEffect } from "react";
import CircularProgress from "@mui/material/CircularProgress";
import Alert from "@mui/material/Alert";
import Collapse from "@mui/material/Collapse";
import IconButton from "@mui/material/IconButton";
import CloseIcon from "@mui/icons-material/Close";

import TextareaAutosize from "../components/InputSection/textareaAutosize";
import { Post } from "../utils/request";

import styles from "./landing.module.css";

const Landing = () => {
  const { uniqueString } = useParams();
  let name = localStorage.getItem("name");
  const [loading, setLoading] = useState(name === undefined ? true : false);
  const [fetching, setFetching] = useState(true);
  const [enteredName, setEnteredName] = useState("");
  const [alertMessage, setAlertMessage] = useState("");

  useEffect(() => {
    const fetchData = async () => {
      const token = localStorage.getItem("token");
      if (token) {
        setLoading(false);
      }
      if (uniqueString) {
        const magic_link = await Post(
          `auth/internal-create-magic-link?user_id=${uniqueString.toString()}`
        );
        if (!magic_link.ok) {
          setAlertMessage("Error occurred");
          return;
        }

        // {new_user: true, token: 'something', user_id}
        const res2 = await Post("auth/exchange", {
          magic_link: magic_link.data,
        });

        if (!res2.ok) {
          setAlertMessage("Error occurred");
          return;
        }
        localStorage.setItem("token", res2.data.token);

        setFetching(false);
      }
    };

    fetchData();
  }, [uniqueString, loading]);

  const handleMessageChange = (e) => {
    setEnteredName(e.target.value);
  };

  const handleSend = async (e) => {
    const setupName = await Post("auth/setup", {
      name: enteredName,
    });

    if (!setupName.ok) {
      setAlertMessage("Submission failed");
      return;
    }

    localStorage.setItem("name", setupName.data.name);
    setLoading(false);
  };

  const loginAndInitSetUp = () => {
    return fetching ? (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "20px",
          marginBottom: "10%",
        }}
      >
        <CircularProgress />
        <div style={{ color: "white" }}>Initializing Lesson</div>
      </div>
    ) : (
      <div className={styles.setUpWrapper}>
        <div>Welcome! Please enter your name!</div>
        <div>
          It will be how you are addressed during conversations and when given
          feedback.
        </div>
        <div className={styles.textAreaWrapper}>
          <div style={{ width: "40%" }}>
            {Boolean(enteredName) && (
              <div style={{ padding: "15px 0 20px 0" }}>Hi {enteredName}!</div>
            )}
            <TextareaAutosize
              value={enteredName}
              onChange={handleMessageChange}
            />
          </div>
        </div>
        <div className={styles.btnWrapper}>
          <div
            style={{
              backgroundColor: Boolean(enteredName) ? "#FFB930" : "#3C3C43",
              color: Boolean(enteredName) ? "#282828" : "#ACACAC",
              cursor: Boolean(enteredName) ? "pointer" : "default",
            }}
            onClick={handleSend}
          >
            Send
          </div>
        </div>
      </div>
    );
  };

  const landingPage = () => {
    return (
      <div className={styles.wrapper}>
        <div className={styles.column}>column</div>
        <div className={styles.columnRight}>
          <Link style={{ color: "white" }} to="/lesson/1">
            Go to first lesson
          </Link>
          <Link style={{ color: "white" }} to="/lesson/2">
            Go to second lesson
          </Link>
        </div>
      </div>
    );
  };

  return (
    <div className={styles.wrapper}>
      {alertMessage && (
        <Collapse in={alertMessage !== ""}>
          <Alert
            action={
              <IconButton
                aria-label="close"
                color="inherit"
                size="small"
                onClick={() => {
                  setAlertMessage(null);
                }}
              >
                <CloseIcon fontSize="inherit" />
              </IconButton>
            }
            sx={{ position: "absolute", top: "20px" }}
            variant="filled"
            severity="warning"
          >
            {alertMessage}
          </Alert>
        </Collapse>
      )}
      {loading ? loginAndInitSetUp() : landingPage()}
    </div>
  );
};

export default Landing;
