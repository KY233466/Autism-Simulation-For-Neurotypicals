import { useState, useRef, useEffect, forwardRef } from "react";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import styles from "./index.module.css";

const ChoicesSection = ({ explanationText, options, handleButtonClick }) => {
  const [isCollapsed, setIsCollapsed] = useState(
    Object.keys(options).length > 1
  );
  const [maxWidth, setMaxWidth] = useState(0);
  const elementsRef = useRef([]);

  useEffect(() => {
    const widths = elementsRef.current.map((el) => (el ? el.offsetWidth : 0));
    setMaxWidth(Math.max(...(widths.length === 0 ? ["100%"] : widths)));
  }, [isCollapsed]);

  return (
    <div className={styles.choicesWrapper}>
      <div
        className={styles.choicesTitlesWrapper}
        style={{
          paddingBottom: isCollapsed ? "0px" : "5px",
          paddingTop: isCollapsed ? "0px" : "15px",
          transform: isCollapsed ? "translate(0px, 10px)" : "translate(0px)",
        }}
      >
        {isCollapsed ? (
          <div></div>
        ) : (
          <div style={{ maxWidth: "60%" }}>
            {Object.keys(options).length === 1
              ? "Click on the option and send"
              : explanationText}
          </div>
        )}
        <div
          className={styles.choice}
          style={{
            display: "flex",
            alignItems: "center",
            fontSize: "14px",
            padding: "3px 4px 4px 10px",
            border: isCollapsed ? "#FFB930 3px solid" : "#42454E 3px solid",
          }}
          onClick={() => setIsCollapsed(!isCollapsed)}
        >
          {isCollapsed ? "View options" : "Hide options"}
          <KeyboardArrowDownIcon
            className={isCollapsed ? styles.arrowRotate : styles.arrow}
          />
        </div>
      </div>
      {!isCollapsed && (
        <div className={styles.choices}>
          {Object.keys(options).map((index) => {
            return (
              <Choice
                width={maxWidth - 25}
                ref={(rel) => (elementsRef.current[index] = rel)}
                key={index}
                message={options[index]}
                func={() => handleButtonClick(index, options[index])}
              />
            );
          })}
        </div>
      )}
    </div>
  );
};

export const Choice = forwardRef(({ width, message, func }, ref) => {
  const style = width ? { width: width } : {};
  return (
    <div ref={ref} className={styles.choice} style={style} onClick={func}>
      {message}
    </div>
  );
});

export default ChoicesSection;
